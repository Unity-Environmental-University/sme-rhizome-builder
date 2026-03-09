import { writable } from 'svelte/store';
import axios from 'axios';

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  canvasBaseUrl: string;
} | null;

export const user = writable<AuthUser>(null);
export const authLoading = writable(true);

export async function loadUser(): Promise<void> {
  try {
    const res = await axios.get('/api/auth/me', { withCredentials: true });
    user.set(res.data);
  } catch (err) {
    // In dev mode, auto-demo-login unless VITE_REQUIRE_LOGIN is set
    if (import.meta.env.DEV && !import.meta.env.VITE_REQUIRE_LOGIN
        && axios.isAxiosError(err) && err.response?.status === 401) {
      try {
        await axios.post('/api/auth/demo', {}, { withCredentials: true });
        const res = await axios.get('/api/auth/me', { withCredentials: true });
        user.set(res.data);
        return;
      } catch {
        // demo login failed — fall through to normal unauthenticated state
      }
    }
    user.set(null);
    if (!axios.isAxiosError(err) || err.response?.status !== 401) {
      console.error('[auth] loadUser failed unexpectedly:', err);
    }
  } finally {
    authLoading.set(false);
  }
}

export async function logout(): Promise<void> {
  try {
    await axios.post('/api/auth/logout', {}, { withCredentials: true });
  } catch (err) {
    // Backend logout failed — still clear local state so the user isn't stuck,
    // but log it so we know the server session may still be live.
    console.error('[auth] logout request failed (clearing local state anyway):', err);
  }
  user.set(null);
}
