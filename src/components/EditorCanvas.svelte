<script context="module" lang="ts">
  export type MarkData = {
    commentId: string;
    source: 'agent' | 'sme' | 'ld';
    unread: boolean;
    // pixel rect relative to this canvas element
    rect: { left: number; top: number; right: number; bottom: number };
  };
</script>

<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let marks: MarkData[] = [];

  let canvas: HTMLCanvasElement;
  let gl: WebGL2RenderingContext;
  let simProg: WebGLProgram;
  let presentProg: WebGLProgram;
  let fbos: WebGLFramebuffer[] = [];
  let textures: WebGLTexture[] = [];
  let quadBuf: WebGLBuffer;
  let pingPong = 0;
  let W = 0, H = 0;
  let rafId: number;
  let startTime: number;
  let observer: ResizeObserver;

  // Uniform locations — cached after compile
  let simLocs: Record<string, WebGLUniformLocation | null> = {};
  let presentLocs: Record<string, WebGLUniformLocation | null> = {};

  // source → [r, g, b, base_intensity]
  const SOURCE_COLORS: Record<string, [number, number, number, number]> = {
    agent: [1.0, 0.82, 0.35, 0.05],  // warm gold, very soft — note slipped under door
    sme:   [1.0, 0.96, 0.85, 0.10],  // warm white, more deliberate
    ld:    [0.65, 0.82, 1.0,  0.08], // cool blue, structural
  };
  const UNREAD_MULTIPLIER = 2.5;
  const MAX_MARKS = 16;

  // ── Shaders ──────────────────────────────────────────────────────────────────

  const vertSrc = `#version 300 es
in vec2 a_pos;
out vec2 v_uv;
void main() {
  v_uv = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

  // Simulation pass: mark-driven heat sources + viscoelastic diffusion
  const simSrc = `#version 300 es
precision highp float;
in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_prev;
uniform vec2 u_resolution;
uniform float u_time;

// Mark heat sources
uniform int u_mark_count;
uniform vec4 u_mark_rects[16];   // xy = min UV, zw = max UV
uniform vec4 u_mark_colors[16];  // rgb = color, a = intensity

// Physics
uniform float u_viscosity;
uniform float u_yield_threshold;
uniform float u_shear_thinning;
uniform float u_diffusion_rate;
uniform float u_anisotropy;
uniform float u_surface_tension;
uniform float u_evaporation;
uniform float u_bloom_radius;
uniform float u_bloom_strength;
uniform float u_chromatic_spread;
uniform float u_warmth;

vec3 getMarkHeat(vec2 uv) {
  vec3 heat = vec3(0.0);
  for (int i = 0; i < 16; i++) {
    if (i >= u_mark_count) break;
    vec4 rect  = u_mark_rects[i];
    vec4 col   = u_mark_colors[i];
    // Soft distance outside the rect boundary
    float dx   = max(0.0, max(rect.x - uv.x, uv.x - rect.z));
    float dy   = max(0.0, max(rect.y - uv.y, uv.y - rect.w));
    float dist = sqrt(dx * dx + dy * dy);
    // Very soft falloff — the note doesn't announce itself
    float f    = exp(-dist * 100.0);
    heat      += col.rgb * col.a * f;
  }
  return heat;
}

void main() {
  vec2 px = 1.0 / u_resolution;

  vec3 current = getMarkHeat(v_uv);
  vec3 prev    = texture(u_prev, v_uv).rgb;

  // Spatial diffusion
  vec3 n  = texture(u_prev, v_uv + vec2(0.0,   px.y)).rgb;
  vec3 s  = texture(u_prev, v_uv - vec2(0.0,   px.y)).rgb;
  vec3 e  = texture(u_prev, v_uv + vec2(px.x,  0.0 )).rgb;
  vec3 w  = texture(u_prev, v_uv - vec2(px.x,  0.0 )).rgb;
  vec3 ne = texture(u_prev, v_uv + vec2( px.x,  px.y)).rgb;
  vec3 nw = texture(u_prev, v_uv + vec2(-px.x,  px.y)).rgb;
  vec3 se = texture(u_prev, v_uv + vec2( px.x, -px.y)).rgb;
  vec3 sw = texture(u_prev, v_uv + vec2(-px.x, -px.y)).rgb;

  vec3 navg     = (n + s + e + w + 0.5*(ne+nw+se+sw)) / 6.0;
  vec3 laplacian = navg - prev;

  vec3 gx = (e - w) * 0.5;
  vec3 gy = (n - s) * 0.5;
  float edge  = length(gx) + length(gy);
  float aniso = 1.0 - u_anisotropy * smoothstep(0.0, 0.15, edge);

  vec3 diffused = prev + laplacian * u_diffusion_rate * aniso;
  diffused += (current - diffused) * u_surface_tension;
  vec3 excess = max(diffused - current, vec3(0.0));
  diffused -= excess * u_evaporation;

  // Viscoelastic blend
  float delta = length(current - diffused);
  float nd    = delta / (delta + u_yield_threshold);
  float flow  = pow(nd, 1.0 / u_shear_thinning);
  float visc  = mix(u_viscosity, u_viscosity * 0.15, flow);
  vec3 blended = mix(current, diffused, visc);

  // Chromatic bloom
  vec3 bloom = vec3(0.0);
  float tw = 0.0;
  for (float x = -3.0; x <= 3.0; x += 1.0) {
    for (float y = -3.0; y <= 3.0; y += 1.0) {
      float d = length(vec2(x, y));
      if (d > 3.5) continue;
      float wt = exp(-d*d / (2.0 * u_bloom_radius));
      vec2 s2 = v_uv + vec2(x, y) * px;
      bloom.r += texture(u_prev, s2 + vec2(u_chromatic_spread, 0.0)*px).r * wt;
      bloom.g += texture(u_prev, s2).g * wt;
      bloom.b += texture(u_prev, s2 - vec2(u_chromatic_spread, 0.0)*px).b * wt;
      tw += wt;
    }
  }
  bloom /= tw;
  blended += bloom * u_bloom_strength;
  blended += vec3(u_warmth, u_warmth*0.4, 0.0) * length(bloom) * u_bloom_strength;

  fragColor = vec4(blended, 1.0);
}`;

  // Presentation pass: vignette + gamma. Screen blend handles transparency.
  const presentSrc = `#version 300 es
precision highp float;
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_tex;
uniform vec2 u_resolution;

void main() {
  vec3 col = texture(u_tex, v_uv).rgb;
  // Subtle vignette on the glow, not the text
  float vig = 1.0 - 0.2 * pow(length((v_uv - 0.5) * vec2(1.5, 1.0)), 2.0);
  col *= vig;
  // Slight gamma warmth
  col = pow(col, vec3(0.96, 0.98, 1.02));
  fragColor = vec4(col, 1.0);
}`;

  // ── GL helpers ────────────────────────────────────────────────────────────────

  function compileShader(src: string, type: number): WebGLShader {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(s) ?? 'shader error');
    }
    return s;
  }

  function createProgram(vs: string, fs: string): WebGLProgram {
    const p = gl.createProgram()!;
    gl.attachShader(p, compileShader(vs, gl.VERTEX_SHADER));
    gl.attachShader(p, compileShader(fs, gl.FRAGMENT_SHADER));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(p) ?? 'link error');
    }
    return p;
  }

  function createFBO(w: number, h: number) {
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.FLOAT, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const fbo = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    return { fbo, tex };
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio, 1.5);
    W = Math.floor(canvas.clientWidth * dpr);
    H = Math.floor(canvas.clientHeight * dpr);
    canvas.width = W;
    canvas.height = H;
    // Recreate FBOs
    textures.forEach(t => gl.deleteTexture(t));
    fbos.forEach(f => gl.deleteFramebuffer(f));
    const a = createFBO(W, H);
    const b = createFBO(W, H);
    fbos = [a.fbo, b.fbo];
    textures = [a.tex, b.tex];
  }

  function setupAttrib(prog: WebGLProgram) {
    const loc = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  }

  function buildMarkArrays(): { rects: Float32Array; colors: Float32Array; count: number } {
    const rects  = new Float32Array(MAX_MARKS * 4);
    const colors = new Float32Array(MAX_MARKS * 4);
    const count  = Math.min(marks.length, MAX_MARKS);
    const cw = canvas.clientWidth  || 1;
    const ch = canvas.clientHeight || 1;

    for (let i = 0; i < count; i++) {
      const m = marks[i];
      const [r, g, b, baseIntensity] = SOURCE_COLORS[m.source] ?? SOURCE_COLORS.agent;
      const intensity = m.unread ? baseIntensity * UNREAD_MULTIPLIER : baseIntensity;

      // Convert pixel rect → UV space
      rects[i*4+0] = m.rect.left   / cw;
      rects[i*4+1] = 1.0 - m.rect.bottom / ch; // flip Y
      rects[i*4+2] = m.rect.right  / cw;
      rects[i*4+3] = 1.0 - m.rect.top    / ch;

      colors[i*4+0] = r;
      colors[i*4+1] = g;
      colors[i*4+2] = b;
      colors[i*4+3] = intensity;
    }
    return { rects, colors, count };
  }

  function render() {
    const time = (performance.now() / 1000) - startTime;
    const { rects, colors, count } = buildMarkArrays();

    const readTex  = textures[pingPong];
    const writeFbo = fbos[1 - pingPong];
    const writeTex = textures[1 - pingPong];

    // Simulation pass
    gl.bindFramebuffer(gl.FRAMEBUFFER, writeFbo);
    gl.viewport(0, 0, W, H);
    gl.useProgram(simProg);
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
    setupAttrib(simProg);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, readTex);
    gl.uniform1i(simLocs.u_prev, 0);
    gl.uniform2f(simLocs.u_resolution, W, H);
    gl.uniform1f(simLocs.u_time, time);
    gl.uniform1i(simLocs.u_mark_count, count);

    if (count > 0) {
      gl.uniform4fv(simLocs['u_mark_rects[0]'],  rects);
      gl.uniform4fv(simLocs['u_mark_colors[0]'], colors);
    }

    // Physics uniforms
    gl.uniform1f(simLocs.u_viscosity,       0.96);
    gl.uniform1f(simLocs.u_yield_threshold, 0.03);
    gl.uniform1f(simLocs.u_shear_thinning,  4.0);
    gl.uniform1f(simLocs.u_diffusion_rate,  0.35);
    gl.uniform1f(simLocs.u_anisotropy,      0.3);
    gl.uniform1f(simLocs.u_surface_tension, 0.015);
    gl.uniform1f(simLocs.u_evaporation,     0.008);
    gl.uniform1f(simLocs.u_bloom_radius,    4.0);
    gl.uniform1f(simLocs.u_bloom_strength,  0.18);
    gl.uniform1f(simLocs.u_chromatic_spread,1.2);
    gl.uniform1f(simLocs.u_warmth,          0.05);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    // Presentation pass
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, W, H);
    gl.useProgram(presentProg);
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
    setupAttrib(presentProg);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, writeTex);
    gl.uniform1i(presentLocs.u_tex, 0);
    gl.uniform2f(presentLocs.u_resolution, W, H);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    pingPong = 1 - pingPong;
    rafId = requestAnimationFrame(render);
  }

  // ── Architecture notes ────────────────────────────────────────────────────────
  //
  // Canvas tracks what's visible, not the full scrollable document. A mark below
  // the fold doesn't glow until it scrolls into view. This is intentional — a note
  // you can't see shouldn't be glowing at you; the sidebar handles awareness of
  // off-screen threads. Edge case to revisit: effects that originate below the fold
  // and bleed upward into view (think tiled scrolling background). Not a concern yet.
  //
  // RAF loop: run economically. When the field is settled (no marks, heat drained),
  // the loop should idle or pause rather than spin. But marks should stay perceptible —
  // not urgent, visible. A very low frequency pulse for unread marks would handle the
  // "occasional reminder" case. Implement this when real marks exist to tune against.
  //
  // Mark rect computation: lazy. Rects are recomputed only when the mark set changes
  // (new comment added, unread status flips), not on every keystroke. AssignmentEditor
  // owns this — it walks the DOM for <mark data-comment-id> elements, calls
  // getBoundingClientRect(), translates to canvas-relative coordinates.
  // TODO: add ResizeObserver on the editor element to catch layout shifts
  // (sidebar open/close, window resize). Not wired yet.
  //
  // TODO: move shader source strings (vertSrc, simSrc, presentSrc) into a separate
  // file (e.g. editorCanvas.glsl.ts or similar). This file is getting long.

  onMount(() => {
    gl = canvas.getContext('webgl2', { antialias: false, alpha: false })!;
    if (!gl) { console.error('[EditorCanvas] WebGL2 not available'); return; }

    // Check for float texture support
    gl.getExtension('EXT_color_buffer_float');

    simProg     = createProgram(vertSrc, simSrc);
    presentProg = createProgram(vertSrc, presentSrc);

    // Cache uniform locations
    for (const name of [
      'u_prev','u_resolution','u_time','u_mark_count',
      'u_mark_rects[0]','u_mark_colors[0]',
      'u_viscosity','u_yield_threshold','u_shear_thinning',
      'u_diffusion_rate','u_anisotropy','u_surface_tension','u_evaporation',
      'u_bloom_radius','u_bloom_strength','u_chromatic_spread','u_warmth',
    ]) {
      simLocs[name] = gl.getUniformLocation(simProg, name);
    }
    for (const name of ['u_tex','u_resolution']) {
      presentLocs[name] = gl.getUniformLocation(presentProg, name);
    }

    quadBuf = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);

    resize();
    startTime = performance.now() / 1000;

    observer = new ResizeObserver(resize);
    observer.observe(canvas.parentElement!);

    rafId = requestAnimationFrame(render);
  });

  onDestroy(() => {
    cancelAnimationFrame(rafId);
    observer?.disconnect();
  });
</script>

<canvas bind:this={canvas} class="editor-canvas"></canvas>

<style lang="scss">
  .editor-canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    mix-blend-mode: screen;
    z-index: 2;
  }
</style>
