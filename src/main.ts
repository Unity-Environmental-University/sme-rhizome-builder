import axios from 'axios';
import App from './App.svelte';
import './styles/global.scss';

// Flask-JWT-Extended requires the CSRF token on mutating requests when using cookie auth.
// The csrf_access_token cookie is readable (not HttpOnly) — read it and send as a header.
axios.interceptors.request.use(config => {
  if (config.method && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    const match = document.cookie.match(/csrf_access_token=([^;]+)/);
    if (match) {
      config.headers['X-CSRF-TOKEN'] = match[1];
    }
  }
  return config;
});

const app = new App({
  target: document.getElementById('app')!
});

export default app;
