<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import axios from 'axios';
  import AssignmentEditor from './AssignmentEditor.svelte';
  import { activeAssignmentId, sidebarOpen } from '../stores/threads';

  type OutcomeRow = { id: number; text: string; position: number };
  type CourseShape = {
    id: number;
    code: string;
    title: string;
    periodType: string;
    outcomes: string[];
    outcomeRows: OutcomeRow[];
  };

  export let assignmentId: string | null = null; // null = new
  export let moduleLabel: string = '';
  export let course: CourseShape;
  export let alignedOutcomes: OutcomeRow[] = [];

  let title = '';
  let content = '';
  let loaded = false;
  let saving = false;
  let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  let autosaveTimer: ReturnType<typeof setTimeout> | null = null;

  const dispatch = createEventDispatcher<{
    saved: { id: string; title: string; moduleLabel: string };
    back: void;
  }>();

  onMount(async () => {
    if (assignmentId) {
      activeAssignmentId.set(assignmentId);
      try {
        // Load latest snapshot
        const res = await axios.get(`/api/assignments/${assignmentId}/snapshots`, { withCredentials: true });
        const snapshots = res.data.snapshots ?? [];
        if (snapshots.length) {
          const latest = snapshots[snapshots.length - 1];
          const snap = typeof latest.content === 'string' ? JSON.parse(latest.content) : latest.content;
          content = snap.description ?? '';
          title = snap.title ?? '';
        }
        // Also get the assignment record for the title
        // (snapshot title might differ from identity record)
      } catch (e) {
        console.error('[AssignmentPane] load failed:', e);
      }
    }
    loaded = true;
  });

  onDestroy(() => {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    activeAssignmentId.set(null);
  });

  function handleContentUpdate(html: string) {
    content = html;
    scheduleAutosave();
  }

  function scheduleAutosave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    if (!assignmentId) return; // can't autosave until created
    autosaveTimer = setTimeout(doAutosave, 2000);
  }

  async function doAutosave() {
    if (!assignmentId || saving) return;
    saving = true;
    saveStatus = 'saving';
    try {
      await axios.post(`/api/assignments/${assignmentId}/snapshots`, {
        content: {
          format_version: '1',
          title: title.trim() || 'Untitled',
          description: content,
          aligned_outcome_ids: alignedOutcomes.map(o => o.id),
        },
        label: 'autosave',
      }, { withCredentials: true });
      saveStatus = 'saved';
      setTimeout(() => { if (saveStatus === 'saved') saveStatus = 'idle'; }, 2000);
    } catch (e) {
      saveStatus = 'error';
      console.error('[AssignmentPane] autosave failed:', e);
    } finally {
      saving = false;
    }
  }

  async function handleSave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);

    if (!assignmentId) {
      // Create the assignment first
      saving = true;
      saveStatus = 'saving';
      try {
        const res = await axios.post('/api/assignments', {
          course_id: course.id,
          title: title.trim() || 'Untitled',
          description: content,
          module_label: moduleLabel,
          aligned_outcome_ids: alignedOutcomes.map(o => o.id),
        }, { withCredentials: true });
        assignmentId = res.data.id;
        activeAssignmentId.set(assignmentId);
        saveStatus = 'saved';
        dispatch('saved', { id: assignmentId!, title: title.trim() || 'Untitled', moduleLabel });
        setTimeout(() => { if (saveStatus === 'saved') saveStatus = 'idle'; }, 2000);
      } catch (e) {
        saveStatus = 'error';
        console.error('[AssignmentPane] create failed:', e);
      } finally {
        saving = false;
      }
    } else {
      // Update title + save snapshot
      saving = true;
      saveStatus = 'saving';
      try {
        const t = title.trim() || 'Untitled';
        await axios.patch(`/api/assignments/${assignmentId}`, { title: t }, { withCredentials: true });
        await axios.post(`/api/assignments/${assignmentId}/snapshots`, {
          content: {
            format_version: '1',
            title: t,
            description: content,
            aligned_outcome_ids: alignedOutcomes.map(o => o.id),
          },
          label: 'draft',
        }, { withCredentials: true });
        saveStatus = 'saved';
        dispatch('saved', { id: assignmentId, title: t, moduleLabel });
        setTimeout(() => { if (saveStatus === 'saved') saveStatus = 'idle'; }, 2000);
      } catch (e) {
        saveStatus = 'error';
        console.error('[AssignmentPane] save failed:', e);
      } finally {
        saving = false;
      }
    }
  }

  function handleTitleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      // Focus the editor body
    }
    scheduleAutosave();
  }

  function goBack() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    sidebarOpen.set(false);
    dispatch('back');
  }
</script>

{#if loaded}
<div class="assignment-pane" in:fade={{ duration: 200 }}>
  <header class="assignment-pane__header">
    <button class="assignment-pane__back" on:click={goBack} aria-label="Back to module">
      ← {moduleLabel}
    </button>
    <span class="assignment-pane__status" class:saving={saveStatus === 'saving'} class:saved={saveStatus === 'saved'} class:error={saveStatus === 'error'}>
      {#if saveStatus === 'saving'}saving…{:else if saveStatus === 'saved'}saved{:else if saveStatus === 'error'}save failed{/if}
    </span>
    <button class="assignment-pane__save" on:click={handleSave} disabled={saving}>
      {assignmentId ? 'save' : 'create'}
    </button>
  </header>

  <div class="assignment-pane__title-area">
    <input
      class="assignment-pane__title"
      type="text"
      placeholder="Assignment title"
      autocomplete="off"
      bind:value={title}
      on:keydown={handleTitleKeydown}
    />
  </div>

  <div class="assignment-pane__editor">
    <AssignmentEditor
      {content}
      assignmentId={assignmentId}
      placeholder="What will students do in {moduleLabel.toLowerCase()}?"
      onUpdate={handleContentUpdate}
    />
  </div>
</div>
{/if}

<style lang="scss">
  .assignment-pane {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: $color-bg-paper;
  }

  .assignment-pane__header {
    display: flex;
    align-items: center;
    gap: $space-md;
    padding: $space-sm $space-lg;
    border-bottom: 1px solid $color-border;
    background: $una-light-green;
    flex-shrink: 0;
  }

  .assignment-pane__back {
    background: none;
    border: none;
    font-family: $font-sans;
    font-size: 0.78rem;
    color: $una-mid-green;
    cursor: pointer;
    padding: $space-xs $space-sm;
    transition: color 160ms ease;

    &:hover { color: $una-dark-1; }
  }

  .assignment-pane__status {
    flex: 1;
    font-family: $font-mono;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: transparent;
    transition: color 300ms ease;

    &.saving { color: $una-mid-green; }
    &.saved { color: $una-mid-green; opacity: 0.6; }
    &.error { color: $una-gold; }
  }

  .assignment-pane__save {
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-xs $space-lg;
    font-family: $font-sans;
    font-size: 0.78rem;
    cursor: pointer;
    letter-spacing: 0.03em;
    transition: background 200ms ease;

    &:hover:not(:disabled) { background: $una-dark-2; }
    &:disabled { opacity: 0.4; cursor: default; }
  }

  .assignment-pane__title-area {
    padding: $space-lg $space-xl $space-sm;
    flex-shrink: 0;
  }

  .assignment-pane__title {
    width: 100%;
    font-family: $font-serif;
    font-size: 1.6rem;
    font-weight: normal;
    border: none;
    background: transparent;
    color: $una-dark-1;
    outline: none;
    line-height: 1.3;

    &::placeholder {
      color: $una-mid-green;
      opacity: 0.5;
      font-style: italic;
    }
  }

  .assignment-pane__editor {
    flex: 1;
    overflow-y: auto;
    padding: 0 $space-xl $space-xl;

    :global(.assignment-editor) {
      border: none;
      min-height: 100%;
    }

    :global(.assignment-editor__toolbar) {
      position: sticky;
      top: 0;
      z-index: 3;
    }
  }
</style>
