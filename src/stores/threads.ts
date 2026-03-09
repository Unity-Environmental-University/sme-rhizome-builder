import { writable } from 'svelte/store';

// Which thread is currently focused in the sidebar. null = none.
export const activeThreadId = writable<string | null>(null);

// Sidebar visibility. Hidden until a thread is opened.
export const sidebarOpen = writable(false);

// Which assignment is currently open in the editor. Set by ModuleView.
export const activeAssignmentId = writable<string | null>(null);

// Incremented to signal the sidebar to re-fetch log entries.
export const logVersion = writable(0);

export function openThread(commentId: string) {
  activeThreadId.set(commentId);
  sidebarOpen.set(true);
}

export function notifyLogChanged() {
  logVersion.update(v => v + 1);
}
