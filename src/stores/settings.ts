import { writable } from 'svelte/store';

export type AiEndpoint = 'anthropic' | 'openai' | 'ollama';

export type Settings = {
  canvasBaseUrl: string;   // informational — actual token comes from OAuth
  apiKey: string;          // API key for whichever AI endpoint is selected
  aiEndpoint: AiEndpoint;  // 'anthropic' | 'openai' (openai covers OpenAI + local)
  aiBaseUrl: string;       // base URL for openai-compatible endpoints (Ollama, LM Studio, etc.)
  aiModel: string;         // optional model override
};

const STORAGE_KEY = 'rhizome_settings';

function loadFromStorage(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const endpoint = parsed.aiEndpoint;
      const validEndpoints: AiEndpoint[] = ['anthropic', 'openai', 'ollama'];
      return {
        canvasBaseUrl: parsed.canvasBaseUrl || defaults().canvasBaseUrl,
        apiKey: parsed.apiKey || '',
        aiEndpoint: validEndpoints.includes(endpoint) ? endpoint : 'anthropic',
        aiBaseUrl: parsed.aiBaseUrl || '',
        aiModel: parsed.aiModel || '',
      };
    }
  } catch (err) {
    console.error('[settings] Failed to read from localStorage:', err);
  }
  return defaults();
}

function defaults(): Settings {
  return {
    canvasBaseUrl: 'https://unity.instructure.com',
    apiKey: '',
    aiEndpoint: 'anthropic',
    aiBaseUrl: '',
    aiModel: '',
  };
}

export const settings = writable<Settings>(loadFromStorage());

settings.subscribe(value => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch (err) {
    console.error('[settings] Failed to persist to localStorage:', err);
  }
});

export function clearSettings(): void {
  localStorage.removeItem(STORAGE_KEY);
  settings.set(defaults());
}
