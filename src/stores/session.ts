import { writable, derived, get } from 'svelte/store';
import axios from 'axios';
import { courseContext } from './courseContext';

export type Message = {
  role: 'user' | 'assistant';
  content: string;
};

export type RubricCriterion = {
  criterion: string;
  long_description: string;
  points: number;
  ratings: { description: string; points: number }[];
};

export type AssignmentDraft = {
  id: string;
  module: string;
  title: string;
  description: string;
  learning_outcomes: string[];
  aligned_outcomes: string[];
  points_possible: number;
  submission_types: string[];
  rubric: RubricCriterion[];
};

export type SessionState = {
  dbSessionId: number | null;
  messages: Message[];
  assignments: AssignmentDraft[];
  loading: boolean;
  error: string | null;
  drawerOpen: boolean;
  drawerIndex: number;
  canvasExporting: boolean;
  canvasExportError: string | null;
  canvasExportUrl: string | null;
};

function storageKey(courseCode: string): string {
  const slug = courseCode.trim().replace(/\s+/g, '_').toLowerCase() || 'default';
  return `rhizome_session_${slug}`;
}

function emptySession(): SessionState {
  return {
    dbSessionId: null,
    messages: [],
    assignments: [],
    loading: false,
    error: null,
    drawerOpen: false,
    drawerIndex: 0,
    canvasExporting: false,
    canvasExportError: null,
    canvasExportUrl: null,
  };
}

function loadFromStorage(): SessionState {
  try {
    const code = get(courseContext).courseCode;
    const raw = localStorage.getItem(storageKey(code));
    if (raw) return { ...emptySession(), ...JSON.parse(raw) };
  } catch (err) {
    console.error('[session] Failed to read from localStorage — starting fresh:', err);
  }
  return emptySession();
}

export const session = writable<SessionState>(loadFromStorage());

session.subscribe(value => {
  try {
    const code = get(courseContext).courseCode;
    localStorage.setItem(storageKey(code), JSON.stringify({
      dbSessionId: value.dbSessionId,
      messages: value.messages,
      assignments: value.assignments,
    }));
  } catch (err) {
    console.error('[session] Failed to persist to localStorage:', err);
  }
});

courseContext.subscribe(ctx => {
  const cached = loadFromStorage();
  session.set(cached);
  if (ctx.id) {
    loadSessionFromApi(ctx.id);
  }
});

export async function loadSessionFromApi(courseId: number): Promise<void> {
  try {
    const summaryRes = await axios.get(`/api/sessions/by-course/${courseId}`, {
      withCredentials: true,
    });
    const { id: sessionId } = summaryRes.data;

    const fullRes = await axios.get(`/api/sessions/${sessionId}`, {
      withCredentials: true,
    });
    const { messages, assignments } = fullRes.data;

    session.update(s => ({
      ...s,
      dbSessionId: sessionId,
      messages: messages ?? s.messages,
      assignments: (assignments ?? s.assignments).map((a: AssignmentDraft) => ({
        ...a,
        module: a.module ?? '',
      })),
      // Clear any stale sync error once we've succeeded
      error: s.error?.startsWith('[sync]') ? null : s.error,
    }));
  } catch (err) {
    // 401 means auth hasn't resolved yet — expected at startup, no noise
    if (axios.isAxiosError(err) && err.response?.status === 401) return;
    console.error('[session] loadSessionFromApi failed — showing cached data:', err);
    session.update(s => ({
      ...s,
      error: '[sync] Could not reach server — showing cached session.',
    }));
  }
}

export const currentAssignment = derived(session, $s =>
  $s.assignments.length > 0 ? $s.assignments[$s.drawerIndex] : null
);

export function resetSession(): void {
  try {
    const code = get(courseContext).courseCode;
    localStorage.removeItem(storageKey(code));
  } catch (err) {
    console.error('[session] Failed to clear localStorage:', err);
  }
  session.set(emptySession());
}
