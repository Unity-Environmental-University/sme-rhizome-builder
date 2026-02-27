<script lang="ts">
  import { onMount } from 'svelte';
  import axios from 'axios';

  let demoAvailable = false;
  let demoLoading = false;

  onMount(async () => {
    // Check if demo is available: 405/422 means endpoint exists but needs POST body,
    // 403 means Canvas OAuth is configured and demo is disabled.
    // We use a HEAD-like GET which will 404 (endpoint is POST-only) rather than 403.
    // Simplest: just try with a flag rather than firing the real endpoint.
    try {
      await axios.get('/api/auth/me', { withCredentials: true });
      // already authed somehow — shouldn't be here, but reload
      window.location.reload();
    } catch {
      // not authed — show demo button only if CANVAS_CLIENT_ID isn't set
      // we detect that by probing the login redirect: if it 503s, no oauth
      try {
        const res = await axios.get('/api/auth/login', {
          withCredentials: true,
          maxRedirects: 0,
          validateStatus: s => s < 400,
        });
        // got a redirect or 200 — oauth is configured
        demoAvailable = false;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 503) {
          demoAvailable = true;
        }
      }
    }
  });

  function signIn() {
    window.location.href = '/api/auth/login';
  }

  async function demoLogin() {
    demoLoading = true;
    try {
      await axios.post('/api/auth/demo', {}, { withCredentials: true });
      window.location.reload();
    } catch (err) {
      demoLoading = false;
    }
  }
</script>

<div class="login">
  <div class="login__card">
    <h1 class="login__title">SME Rhizome Builder</h1>
    <p class="login__tagline">Explore your discipline. Shape an assignment that belongs to it.</p>
    <button class="login__btn" type="button" on:click={signIn}>
      Sign in with Canvas
    </button>
    {#if demoAvailable}
      <button class="login__demo" type="button" on:click={demoLogin} disabled={demoLoading}>
        {demoLoading ? 'entering…' : 'try demo'}
      </button>
    {/if}
    <p class="login__note">
      Your session and assignments are saved to your account —<br>
      not just your browser.
    </p>
  </div>
</div>

<style lang="scss">
  .login {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $color-bg-body;
  }

  .login__card {
    background: $color-bg-paper;
    border-top: $border-top;
    box-shadow: $shadow-paper;
    padding: $space-xl $space-xl;
    max-width: 400px;
    width: 100%;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-md;
  }

  .login__title {
    font-family: $font-serif;
    font-size: 1.8rem;
    font-weight: normal;
    margin: 0;
    color: $una-dark-1;
  }

  .login__tagline {
    font-family: $font-serif;
    font-size: 0.95rem;
    color: $una-mid-green;
    font-style: italic;
    margin: 0;
    line-height: 1.5;
  }

  .login__btn {
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-sm $space-xl;
    font-family: $font-sans;
    font-size: 1rem;
    cursor: pointer;
    letter-spacing: 0.04em;
    margin-top: $space-sm;

    &:hover {
      background: $una-dark-2;
    }
  }

  .login__demo {
    background: none;
    border: 1px solid $color-border;
    color: $una-mid-green;
    padding: $space-xs $space-lg;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;
    letter-spacing: 0.04em;

    &:hover:not(:disabled) {
      border-color: $una-mid-green;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  .login__note {
    font-family: $font-sans;
    font-size: 0.78rem;
    color: $una-mid-green;
    margin: 0;
    line-height: 1.5;
  }
</style>
