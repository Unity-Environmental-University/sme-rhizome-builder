<script lang="ts">
  import { onDestroy } from 'svelte';
  import axios from 'axios';
  import { activeThreadId, activeAssignmentId, sidebarOpen, logVersion } from '../stores/threads';

  type PulseReading = {
    text: string;
    likelihood: number;
    statements: { text: string; observed: boolean | null }[];
  };

  type LogEntry = {
    id: number;
    user_id: number;
    context_type: string;
    context_id: string;
    action_type: string;
    content: string;
    replied_to: number | null;
    created_at: string;
    // parsed from content JSON
    _parsed?: { comment_id?: string; text?: string; source?: string; pulse?: PulseReading[] };
  };

  let entries: LogEntry[] = [];
  let thread: LogEntry[] = [];
  let replyText = '';
  let submitting = false;
  let fetchError = '';

  async function fetchLog(assignmentId: string) {
    fetchError = '';
    try {
      const res = await axios.get(`/api/log/${assignmentId}`, { withCredentials: true });
      entries = (res.data.entries as LogEntry[]).map(e => {
        let _parsed: LogEntry['_parsed'] = {};
        try { _parsed = JSON.parse(e.content); } catch { _parsed = {}; }
        return { ...e, _parsed };
      });
    } catch (e) {
      fetchError = 'Could not load thread.';
      console.error('[ThreadSidebar] fetch error:', e);
    }
  }

  function buildThread(allEntries: LogEntry[], commentId: string | null): LogEntry[] {
    if (!commentId) return [];
    // root: entries whose parsed content has comment_id === commentId
    const roots = allEntries.filter(e => e._parsed?.comment_id === commentId);
    if (!roots.length) return [];
    // replies: entries whose replied_to points to a root or another reply in this thread
    const rootIds = new Set(roots.map(e => e.id));
    const replies = allEntries.filter(e => e.replied_to !== null && rootIds.has(e.replied_to));
    return [...roots, ...replies].sort((a, b) => a.id - b.id);
  }

  // React to store changes
  let unsubThread: () => void;
  let unsubAssignment: () => void;
  let currentAssignmentId: string | null = null;
  let currentThreadId: string | null = null;

  unsubAssignment = activeAssignmentId.subscribe(id => {
    currentAssignmentId = id;
    if (id) fetchLog(id);
    else { entries = []; thread = []; }
  });

  unsubThread = activeThreadId.subscribe(commentId => {
    currentThreadId = commentId;
    thread = buildThread(entries, commentId);
  });

  // Re-build thread whenever entries refresh
  $: thread = buildThread(entries, currentThreadId);

  // Re-fetch when the log changes (e.g. concierge responds)
  let unsubVersion: () => void;
  unsubVersion = logVersion.subscribe(() => {
    if (currentAssignmentId) fetchLog(currentAssignmentId);
  });

  function close() {
    sidebarOpen.set(false);
    activeThreadId.set(null);
  }

  async function submitReply() {
    if (!replyText.trim() || !currentAssignmentId || !currentThreadId) return;
    submitting = true;
    try {
      const root = thread[0];
      await axios.post(`/api/log/${currentAssignmentId}`, {
        action_type: 'comment',
        content: JSON.stringify({ comment_id: currentThreadId, text: replyText.trim(), source: 'sme' }),
        replied_to: root?.id ?? null,
      }, { withCredentials: true });
      replyText = '';
      await fetchLog(currentAssignmentId);
    } catch (e) {
      console.error('[ThreadSidebar] reply failed:', e);
    } finally {
      submitting = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submitReply();
  }

  onDestroy(() => {
    unsubThread();
    unsubAssignment();
    unsubVersion();
  });

  function sourceBadge(entry: LogEntry): string {
    if (entry.action_type === 'bearing_pulse') return 'bearing';
    return entry._parsed?.source ?? (entry.action_type === 'agent_note' ? 'agent' : 'sme');
  }

  function entryText(entry: LogEntry): string {
    return entry._parsed?.text ?? entry.content;
  }

  function getPulse(entry: LogEntry): PulseReading[] {
    return (entry._parsed?.pulse ?? []) as PulseReading[];
  }

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
</script>

<aside class="thread-sidebar">
  <header class="thread-sidebar__header">
    <span class="thread-sidebar__title">thread</span>
    <button class="thread-sidebar__close" on:click={close} aria-label="Close sidebar">✕</button>
  </header>

  <div class="thread-sidebar__body">
    {#if fetchError}
      <p class="thread-sidebar__error">{fetchError}</p>
    {:else if thread.length === 0}
      <p class="thread-sidebar__empty">Nothing here yet.</p>
    {:else}
      <ul class="thread-sidebar__entries" role="list">
        {#each thread as entry (entry.id)}
          <li class="thread-sidebar__entry" data-source={sourceBadge(entry)}>
            <span class="thread-sidebar__source" data-source={sourceBadge(entry)}>{sourceBadge(entry)}</span>
            {#if entry.action_type === 'bearing_pulse' && entry._parsed?.pulse}
              <div class="thread-sidebar__pulse">
                {#each getPulse(entry) as reading}
                  <div class="pulse__bearing">
                    <span class="pulse__likelihood" class:pulse--go={reading.likelihood >= 0.6} class:pulse--nogo={reading.likelihood < 0.4}>{(reading.likelihood * 100).toFixed(0)}%</span>
                    <span class="pulse__text">{reading.text}</span>
                  </div>
                  {#each reading.statements as stmt}
                    <span class="pulse__stmt" class:pulse__stmt--confirmed={stmt.observed === true} class:pulse__stmt--disconfirmed={stmt.observed === false} class:pulse__stmt--unaddressed={stmt.observed === null}>{stmt.text}</span>
                  {/each}
                {/each}
              </div>
            {:else}
              <p class="thread-sidebar__text">{entryText(entry)}</p>
            {/if}
            <time class="thread-sidebar__time" datetime={entry.created_at}>{formatTime(entry.created_at)}</time>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <footer class="thread-sidebar__footer">
    <textarea
      class="thread-sidebar__reply"
      placeholder="Add a note… (⌘↵ to send)"
      bind:value={replyText}
      on:keydown={handleKeydown}
      rows="3"
    ></textarea>
    <button
      class="thread-sidebar__submit"
      on:click={submitReply}
      disabled={submitting || !replyText.trim()}
    >{submitting ? '…' : 'send'}</button>
  </footer>
</aside>

<style lang="scss">
  .thread-sidebar {
    display: flex;
    flex-direction: column;
    height: 100vh;
    border-left: 1px solid $color-border;
    background: $color-bg-paper;
    font-family: $font-sans;
    overflow: hidden;
    position: sticky;
    top: 0;
  }

  .thread-sidebar__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $space-sm $space-md;
    border-bottom: 1px solid $color-border;
    background: $una-light-green;
    flex-shrink: 0;
  }

  .thread-sidebar__title {
    font-family: $font-mono;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: $una-mid-green;
  }

  .thread-sidebar__close {
    background: none;
    border: none;
    color: $una-mid-green;
    cursor: pointer;
    font-size: 0.85rem;
    padding: $space-xs;
    line-height: 1;
    transition: color 160ms ease;

    &:hover { color: $una-dark-1; }
  }

  .thread-sidebar__body {
    flex: 1;
    overflow-y: auto;
    padding: $space-md;
  }

  .thread-sidebar__empty,
  .thread-sidebar__error {
    font-size: 0.82rem;
    color: $una-mid-green;
    font-style: italic;
    margin: 0;
  }

  .thread-sidebar__error { color: $color-text; }

  .thread-sidebar__entries {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: $space-md;
  }

  .thread-sidebar__entry {
    border-left: 2px solid var(--mark-color, $color-border);
    padding-left: $space-sm;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .thread-sidebar__source {
    font-family: $font-mono;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: $una-mid-green;
  }

  .thread-sidebar__text {
    font-size: 0.85rem;
    line-height: 1.55;
    color: $color-text;
    margin: 0;
  }

  .thread-sidebar__time {
    font-family: $font-mono;
    font-size: 0.6rem;
    color: $una-mid-green;
    opacity: 0.7;
  }

  .thread-sidebar__pulse {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .pulse__bearing {
    display: flex;
    align-items: baseline;
    gap: $space-xs;
  }

  .pulse__likelihood {
    font-family: $font-mono;
    font-size: 0.75rem;
    font-weight: 600;
    min-width: 2.5em;
  }

  .pulse--go { color: $una-mid-green; }
  .pulse--nogo { color: #b35540; }

  .pulse__text {
    font-size: 0.78rem;
    color: $color-text;
  }

  .pulse__stmt {
    font-size: 0.7rem;
    padding-left: 2.5em;
    line-height: 1.4;
  }

  .pulse__stmt--confirmed { color: $una-mid-green; }
  .pulse__stmt--confirmed::before { content: "\2713\00a0"; }
  .pulse__stmt--disconfirmed { color: #b35540; }
  .pulse__stmt--disconfirmed::before { content: "\2717\00a0"; }
  .pulse__stmt--unaddressed { color: $una-mid-green; opacity: 0.5; }
  .pulse__stmt--unaddressed::before { content: "\2014\00a0"; }

  .thread-sidebar__footer {
    border-top: 1px solid $color-border;
    padding: $space-sm $space-md;
    display: flex;
    flex-direction: column;
    gap: $space-xs;
    flex-shrink: 0;
    background: $una-light-green;
  }

  .thread-sidebar__reply {
    width: 100%;
    font-family: $font-sans;
    font-size: 0.82rem;
    border: 1px solid $color-border;
    background: $color-bg-paper;
    color: $color-text;
    padding: $space-xs $space-sm;
    resize: none;
    outline: none;
    line-height: 1.5;
    transition: border-color 160ms ease;

    &:focus { border-color: $una-mid-green; }
    &::placeholder { color: $una-mid-green; opacity: 0.7; }
  }

  .thread-sidebar__submit {
    align-self: flex-end;
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-xs $space-md;
    font-family: $font-sans;
    font-size: 0.78rem;
    cursor: pointer;
    letter-spacing: 0.03em;
    transition: background 200ms ease;

    &:hover:not(:disabled) { background: $una-dark-2; }
    &:disabled { opacity: 0.4; cursor: default; }
  }
</style>
