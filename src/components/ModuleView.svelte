<script lang="ts">
  import { fade, fly } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';
  import { createEventDispatcher } from 'svelte';
  import axios from 'axios';
  import AssignmentEditor from './AssignmentEditor.svelte';
  import ThreadSidebar from './ThreadSidebar.svelte';
  import { activeAssignmentId, sidebarOpen } from '../stores/threads';

  type OutcomeRow = { id: number; text: string; position: number };
  type AssignmentSnapshot = { id: number; label: string | null; description: string };
  type AssignmentStub = {
    id: string;
    title: string;
    module_label: string;
    position: number | null;
    snapshot: AssignmentSnapshot | null;
  };
  type ModuleShape = {
    id: number;
    week: number;
    title: string;
    description: string;
    outcomeIds: number[];
    assignments: AssignmentStub[];
  };
  type CourseShape = {
    id: number;
    code: string;
    title: string;
    description: string;
    periodType: string;
    outcomes: string[];
    outcomeRows: OutcomeRow[];
  };

  export let activeModule: ModuleShape;
  export let activeOutcomes: OutcomeRow[];
  export let course: CourseShape;

  // null = editor closed, '' = new assignment, '<uuid>' = editing existing
  let editingId: string | null = null;
  let assignmentTitle = '';
  let editorContent = '';
  let editorKey = 0; // force TipTap remount when switching assignments
  let saving = false;

  $: editorOpen = editingId !== null;
  $: isNew = editingId === '';

  const dispatch = createEventDispatcher<{
    assignmentSaved: AssignmentStub;
    assignmentsReordered: { week: number; assignments: AssignmentStub[] };
  }>();

  function openNew() {
    assignmentTitle = '';
    editorContent = '';
    editorKey += 1;
    editingId = '';
    activeAssignmentId.set(null);
  }

  function openExisting(a: AssignmentStub) {
    assignmentTitle = a.title;
    editorContent = a.snapshot?.description ?? '';
    editorKey += 1;
    editingId = a.id;
    activeAssignmentId.set(a.id);
  }

  function closeEditor() {
    editingId = null;
    assignmentTitle = '';
    editorContent = '';
    activeAssignmentId.set(null);
    sidebarOpen.set(false);
  }

  async function saveAssignment() {
    if (saving) return;
    saving = true;
    try {
      if (isNew) {
        const res = await axios.post('/api/assignments', {
          course_id: course.id,
          title: assignmentTitle.trim() || 'Untitled',
          description: editorContent,
          module_label: `${course.periodType} ${activeModule.week}`,
          aligned_outcome_ids: activeOutcomes.map(o => o.id),
        }, { withCredentials: true });
        dispatch('assignmentSaved', res.data as AssignmentStub);
      } else {
        // Update title if changed, then write a new snapshot with current content
        const title = assignmentTitle.trim() || 'Untitled';
        await axios.patch(`/api/assignments/${editingId}`, { title }, { withCredentials: true });
        await axios.post(`/api/assignments/${editingId}/snapshots`, {
          content: {
            format_version: '1',
            title,
            description: editorContent,
            aligned_outcome_ids: activeOutcomes.map(o => o.id),
          },
          label: 'draft',
        }, { withCredentials: true });
        // Reflect updated content locally
        dispatch('assignmentSaved', {
          id: editingId,
          title,
          module_label: `${course.periodType} ${activeModule.week}`,
          position: null,
          snapshot: { id: 0, label: 'draft', description: editorContent },
        } as AssignmentStub);
      }
      closeEditor();
    } catch (e) {
      console.error('[ModuleView] save failed:', e);
    } finally {
      saving = false;
    }
  }

  async function moveAssignment(index: number, dir: -1 | 1) {
    const newIndex = index + dir;
    if (newIndex < 0 || newIndex >= activeModule.assignments.length) return;

    const list = [...activeModule.assignments];
    [list[index], list[newIndex]] = [list[newIndex], list[index]];
    dispatch('assignmentsReordered', { week: activeModule.week, assignments: list });

    try {
      await Promise.all(list.map((a, i) =>
        axios.patch(`/api/assignments/${a.id}`, { position: i }, { withCredentials: true })
      ));
    } catch (e) {
      console.error('[ModuleView] reorder failed:', e);
    }
  }
</script>

<article class="module-view" in:fade={{ duration: 320, delay: 80 }}>
  <header class="module-view__header">
    <p class="module-view__week">{course.periodType} {activeModule.week}</p>
    <h1
      class="module-view__title"
      in:fly={{ y: 8, duration: 340, delay: 60, easing: quintOut }}
    >{activeModule.title}</h1>
  </header>

  <section
    class="module-view__context"
    in:fly={{ y: 10, duration: 360, delay: 100, easing: quintOut }}
    aria-label="Week context"
  >
    <p class="module-view__description">{activeModule.description}</p>

    {#if activeOutcomes.length > 0}
      <div class="module-view__outcomes" aria-label="Connected outcomes">
        <span class="module-view__outcomes-label">outcomes</span>
        {#each activeOutcomes as o, i}
          <span
            class="module-view__outcome-chip"
            title={o.text}
            in:fade={{ duration: 200, delay: 180 + i * 60 }}
          >{o.position + 1}</span>
        {/each}
      </div>
    {/if}
  </section>

  <section
    class="module-view__assignments"
    aria-label="Assignments"
    in:fly={{ y: 10, duration: 360, delay: 160, easing: quintOut }}
  >
    {#if activeModule.assignments.length > 0}
      <ul class="module-view__assignment-list" role="list">
        {#each activeModule.assignments as a, i}
          <li
            class="module-view__assignment"
            in:fly={{ x: 8, duration: 280, delay: i * 60, easing: quintOut }}
          >
            <span class="module-view__assignment-label">{course.periodType} {activeModule.week}</span>
            <button
              class="module-view__assignment-name"
              on:click={() => openExisting(a)}
              aria-label="Open {a.title}"
            >{a.title}</button>
            <span class="module-view__draft">draft</span>
            <span class="module-view__reorder" aria-label="Reorder">
              <button
                class="module-view__reorder-btn"
                on:click={() => moveAssignment(i, -1)}
                disabled={i === 0}
                aria-label="Move up"
              >↑</button>
              <button
                class="module-view__reorder-btn"
                on:click={() => moveAssignment(i, 1)}
                disabled={i === activeModule.assignments.length - 1}
                aria-label="Move down"
              >↓</button>
            </span>
          </li>
        {/each}
      </ul>
    {/if}

    {#if !editorOpen}
      <button
        class="module-view__add"
        on:click={openNew}
        in:fade={{ duration: 280, delay: 200 }}
      >
        + add assignment
      </button>
    {/if}
  </section>

  {#if editorOpen}
    <section
      class="module-view__editor"
      aria-label="{isNew ? 'New' : 'Edit'} assignment"
      in:fly={{ y: 20, duration: 440, easing: quintOut }}
    >
      <header class="module-view__editor-header">
        <input
          class="module-view__title-input"
          type="text"
          placeholder="Assignment title"
          autocomplete="off"
          bind:value={assignmentTitle}
        />
        <button
          class="module-view__editor-close"
          on:click={closeEditor}
          aria-label="Close editor"
        >✕</button>
      </header>

      <div class="module-view__editor-area" class:sidebar-open={$sidebarOpen}>
        <div class="module-view__editor-main">
          {#key editorKey}
            <AssignmentEditor
              content={editorContent}
              assignmentId={editingId || null}
              placeholder="What will students do in {course.periodType.toLowerCase()} {activeModule.week}?"
              onUpdate={(html) => { editorContent = html; }}
            />
          {/key}
        </div>
        {#if $sidebarOpen}
          <div class="module-view__thread-panel">
            <ThreadSidebar />
          </div>
        {/if}
      </div>

      <footer class="module-view__editor-footer">
        <button
          class="module-view__save"
          on:click={saveAssignment}
          disabled={saving}
        >{saving ? 'saving…' : 'save draft'}</button>
      </footer>
    </section>
  {/if}
</article>

<style lang="scss">
  .module-view__header {
    margin-bottom: $space-lg;
    border-top: $border-top;
    padding-top: $space-md;
  }

  .module-view__week {
    font-family: $font-mono;
    font-size: 0.68rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 $space-xs;
  }

  .module-view__title {
    font-family: $font-serif;
    font-size: 1.9rem;
    font-weight: normal;
    color: $una-dark-1;
    margin: 0;
    line-height: 1.2;
  }

  .module-view__context {
    margin-bottom: $space-xl;
    padding-bottom: $space-xl;
    border-bottom: 1px solid $color-border;
  }

  .module-view__description {
    font-family: $font-serif;
    font-size: 0.95rem;
    line-height: 1.75;
    color: $color-text;
    margin: 0 0 $space-md;
  }

  .module-view__outcomes {
    display: flex;
    align-items: center;
    gap: $space-sm;
    flex-wrap: wrap;
  }

  .module-view__outcomes-label {
    font-family: $font-sans;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: $una-mid-green;
    margin-right: $space-xs;
  }

  .module-view__outcome-chip {
    font-family: $font-mono;
    font-size: 0.72rem;
    color: $una-mid-green;
    border: 1px solid $color-border;
    padding: 2px 7px;
    cursor: default;
    transition: border-color 200ms ease, color 200ms ease;

    &:hover {
      border-color: $una-gold;
      color: $una-dark-1;
    }
  }

  .module-view__assignments {
    margin-bottom: $space-xl;
  }

  .module-view__assignment-list {
    list-style: none;
    margin: 0 0 $space-md;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: $space-xs;
  }

  .module-view__assignment {
    display: flex;
    align-items: center;
    gap: $space-sm;
    padding: $space-sm 0;
    border-bottom: 1px solid $color-border;
  }

  .module-view__assignment-label {
    font-family: $font-mono;
    font-size: 0.65rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    flex-shrink: 0;
  }

  .module-view__assignment-name {
    font-family: $font-sans;
    font-size: 0.9rem;
    color: $una-dark-1;
    flex: 1;
    background: none;
    border: none;
    padding: 0;
    text-align: left;
    cursor: pointer;
    transition: color 160ms ease;

    &:hover { color: $una-mid-green; }
  }

  .module-view__draft {
    font-family: $font-mono;
    font-size: 0.65rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border: 1px solid $color-border;
    padding: 2px $space-xs;
    flex-shrink: 0;
  }

  .module-view__reorder {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .module-view__reorder-btn {
    background: none;
    border: 1px solid transparent;
    color: $una-mid-green;
    font-size: 0.75rem;
    padding: 1px 4px;
    cursor: pointer;
    line-height: 1;
    transition: border-color 160ms ease, color 160ms ease;

    &:hover:not(:disabled) {
      border-color: $color-border;
      color: $una-dark-1;
    }

    &:disabled {
      opacity: 0.25;
      cursor: default;
    }
  }

  .module-view__add {
    background: none;
    border: 1px dashed $color-border;
    color: $una-mid-green;
    font-family: $font-sans;
    font-size: 0.82rem;
    padding: $space-sm $space-md;
    cursor: pointer;
    transition: border-color 240ms ease, color 240ms ease;

    &:hover {
      border-color: $una-mid-green;
      color: $una-dark-1;
    }
  }

  .module-view__editor {
    border: 1px solid $color-border;
    background: $color-bg-paper;
    box-shadow: $shadow-paper;
  }

  .module-view__editor-header {
    display: flex;
    align-items: center;
    gap: $space-sm;
    padding: $space-md $space-lg;
    border-bottom: 1px solid $color-border;
    background: $una-light-green;
  }

  .module-view__title-input {
    flex: 1;
    font-family: $font-serif;
    font-size: 1.1rem;
    border: none;
    background: transparent;
    color: $una-dark-1;
    outline: none;

    &::placeholder {
      color: $una-mid-green;
      opacity: 0.6;
      font-style: italic;
    }
  }

  .module-view__editor-close {
    background: none;
    border: none;
    color: $una-mid-green;
    cursor: pointer;
    font-size: 0.9rem;
    padding: $space-xs;
    transition: color 160ms ease;

    &:hover { color: $una-dark-1; }
  }

  .module-view__editor-area {
    display: flex;
    min-height: 320px;

    &.sidebar-open {
      .module-view__editor-main { flex: 1; min-width: 0; }
    }
  }

  .module-view__editor-main {
    flex: 1;
    min-width: 0;
  }

  .module-view__thread-panel {
    width: 280px;
    flex-shrink: 0;
  }

  .module-view__editor-footer {
    display: flex;
    justify-content: flex-end;
    padding: $space-sm $space-lg;
    border-top: 1px solid $color-border;
    background: $una-light-green;
  }

  .module-view__save {
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-sm $space-xl;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;
    letter-spacing: 0.03em;
    transition: background 240ms ease;

    &:hover { background: $una-dark-2; }
  }
</style>
