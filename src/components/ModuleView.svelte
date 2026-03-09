<script lang="ts">
  import { fade, fly } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';
  import { createEventDispatcher } from 'svelte';
  import axios from 'axios';

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

  const dispatch = createEventDispatcher<{
    openAssignment: { assignmentId: string };
    newAssignment: void;
    assignmentsReordered: { week: number; assignments: AssignmentStub[] };
  }>();

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
              on:click={() => dispatch('openAssignment', { assignmentId: a.id })}
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

    <button
      class="module-view__add"
      on:click={() => dispatch('newAssignment')}
      in:fade={{ duration: 280, delay: 200 }}
    >
      + add assignment
    </button>
  </section>
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
</style>
