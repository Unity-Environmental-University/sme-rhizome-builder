"""
Admin settings dashboard — localhost only.

GET  /admin          → HTML form showing current .env state
POST /admin/settings → save values to .env

Writes to ../.env (repo root). Restart Flask to pick up changes.
Not registered when ADMIN_DISABLED=1.
"""

import os
import re

from flask import Blueprint, abort, jsonify, request

admin_bp = Blueprint("admin", __name__)

# .env lives at repo root, one level above backend/
_ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

SETTINGS = [
    {
        "key": "ANTHROPIC_API_KEY",
        "label": "Anthropic API Key",
        "secret": True,
        "hint": "sk-ant-…  ·  console.anthropic.com",
    },
    {
        "key": "CANVAS_CLIENT_ID",
        "label": "Canvas Client ID",
        "secret": False,
        "hint": "Admin → Developer Keys → + API Key",
    },
    {
        "key": "CANVAS_CLIENT_SECRET",
        "label": "Canvas Client Secret",
        "secret": True,
        "hint": "Shown once when you create the key",
    },
    {
        "key": "CANVAS_BASE_URL",
        "label": "Canvas Base URL",
        "secret": False,
        "hint": "https://unity.instructure.com",
    },
    {
        "key": "CANVAS_OAUTH_REDIRECT_URI",
        "label": "OAuth Redirect URI",
        "secret": False,
        "hint": "http://localhost:5050/api/auth/callback",
    },
    {
        "key": "JWT_SECRET_KEY",
        "label": "JWT Secret Key",
        "secret": True,
        "hint": "Any long random string — keep it stable",
    },
]

_ALLOWED_KEYS = {s["key"] for s in SETTINGS}


def _localhost_only():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)


def _read_env() -> dict:
    result = {}
    if not os.path.exists(_ENV_FILE):
        return result
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)", line)
            if m:
                val = m.group(2).strip().strip('"').strip("'")
                result[m.group(1)] = val
    return result


def _write_env(updates: dict):
    """Merge updates into .env, preserving existing lines and comments."""
    lines = []
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE) as f:
            lines = f.readlines()

    written = set()
    new_lines = []
    for line in lines:
        m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", line.strip())
        if m and m.group(1) in updates:
            key = m.group(1)
            new_lines.append(f"{key}={updates[key]}\n")
            written.add(key)
        else:
            new_lines.append(line)

    for key, val in updates.items():
        if key not in written:
            new_lines.append(f"{key}={val}\n")

    with open(_ENV_FILE, "w") as f:
        f.writelines(new_lines)


def _mask(val: str) -> str:
    if not val:
        return ""
    return val[:4] + "••••" if len(val) > 8 else "••••••••"


@admin_bp.get("/admin")
def admin_page():
    _localhost_only()
    env = _read_env()
    # Overlay live env vars (set outside .env)
    for key in _ALLOWED_KEYS:
        if key not in env and os.environ.get(key):
            env[key] = os.environ[key]

    rows_html = ""
    for s in SETTINGS:
        val = env.get(s["key"], "")
        is_set = bool(val)
        status_cls = "is-set" if is_set else "not-set"
        status_txt = "set" if is_set else "not set"
        display = _mask(val) if s["secret"] else val
        input_type = "password" if s["secret"] else "text"
        placeholder = display if s["secret"] else s["hint"]
        input_val = "" if s["secret"] else display

        rows_html += f"""
      <div class="row">
        <div class="row-label">
          <span class="key">{s['key']}</span>
          <span class="badge {status_cls}">{status_txt}</span>
        </div>
        <p class="hint">{s['hint']}</p>
        <input
          type="{input_type}"
          name="{s['key']}"
          placeholder="{placeholder}"
          value="{input_val}"
          autocomplete="off"
          spellcheck="false"
        />
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rhizome — Settings</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      background: #f0ede6;
      color: #1a1a1a;
      padding: 2.5rem 1.5rem;
      min-height: 100vh;
    }}
    .wrap {{ max-width: 560px; margin: 0 auto; }}
    h1 {{ font-size: 1rem; font-weight: 600; letter-spacing: 0.01em; margin-bottom: 0.2rem; }}
    .sub {{ font-size: 0.75rem; color: #888; margin-bottom: 2rem; }}
    .card {{
      background: #fff;
      border-radius: 8px;
      padding: 1.75rem;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    .row {{ margin-bottom: 1.4rem; }}
    .row:last-of-type {{ margin-bottom: 0; }}
    .row-label {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.2rem;
    }}
    .key {{
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 0.8rem;
      font-weight: 600;
    }}
    .badge {{
      font-size: 0.65rem;
      padding: 1px 6px;
      border-radius: 10px;
      font-weight: 500;
    }}
    .is-set  {{ background: #d4edda; color: #155724; }}
    .not-set {{ background: #f8d7da; color: #721c24; }}
    .hint {{ font-size: 0.72rem; color: #999; margin-bottom: 0.4rem; }}
    input {{
      width: 100%;
      padding: 0.45rem 0.6rem;
      border: 1px solid #ddd;
      border-radius: 5px;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 0.8rem;
      color: #1a1a1a;
      background: #fafafa;
      transition: border-color 150ms;
    }}
    input:focus {{ outline: none; border-color: #4a7c59; background: #fff; }}
    input::placeholder {{ color: #bbb; }}
    .divider {{ border: none; border-top: 1px solid #eee; margin: 1.5rem 0; }}
    .actions {{ display: flex; align-items: center; gap: 1rem; }}
    button {{
      background: #2d4a38;
      color: #fff;
      border: none;
      padding: 0.5rem 1.4rem;
      border-radius: 5px;
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 150ms;
    }}
    button:hover {{ background: #1a2f22; }}
    button:disabled {{ background: #aaa; cursor: default; }}
    #msg {{ font-size: 0.78rem; color: #4a7c59; }}
    #msg.error {{ color: #b33; }}
    .note {{ font-size: 0.72rem; color: #aaa; margin-top: 1.25rem; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Rhizome Builder — Server Settings</h1>
    <p class="sub">localhost only &nbsp;·&nbsp; writes to .env &nbsp;·&nbsp; restart Flask to apply</p>
    <div class="card">
      <form id="form">
        {rows_html}
        <hr class="divider">
        <div class="actions">
          <button type="submit" id="btn">Save to .env</button>
          <span id="msg"></span>
        </div>
      </form>
      <p class="note">
        Secret fields: leave blank to keep the existing value.<br>
        Changes take effect after restarting Flask (<code>npm run dev:full</code>).
      </p>
    </div>
  </div>
  <script>
    const form = document.getElementById('form');
    const btn  = document.getElementById('btn');
    const msg  = document.getElementById('msg');

    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      btn.disabled = true;
      msg.textContent = 'Saving…';
      msg.className = '';

      const data = {{}};
      form.querySelectorAll('input').forEach(inp => {{
        const v = inp.value.trim();
        // Skip blanks and anything that looks like our mask placeholder
        if (v && !v.includes('••')) data[inp.name] = v;
      }});

      try {{
        const res = await fetch('/admin/settings', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(data),
        }});
        const json = await res.json();
        if (json.ok) {{
          msg.textContent = 'Saved. Restart Flask to apply.';
          setTimeout(() => location.reload(), 1500);
        }} else {{
          msg.textContent = json.error || 'Unknown error';
          msg.className = 'error';
        }}
      }} catch (err) {{
        msg.textContent = 'Request failed';
        msg.className = 'error';
      }} finally {{
        btn.disabled = false;
      }}
    }});
  </script>
</body>
</html>"""


@admin_bp.post("/admin/settings")
def admin_save():
    _localhost_only()
    body = request.get_json(force=True) or {}
    filtered = {k: str(v).strip() for k, v in body.items() if k in _ALLOWED_KEYS and v}
    if not filtered:
        return jsonify({"ok": True, "note": "nothing to save"})
    _write_env(filtered)
    return jsonify({"ok": True, "saved": list(filtered.keys())})
