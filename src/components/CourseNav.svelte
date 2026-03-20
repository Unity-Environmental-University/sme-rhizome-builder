<script lang="ts">
  import { fly } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';
  import { createEventDispatcher } from 'svelte';

  type OutcomeRow = { id: number; text: string; position: number };
  type AssignmentStub = { id: string; title: string; module_label: string; position: number | null; snapshot: unknown };
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
  type View = { kind: 'course' } | { kind: 'module'; week: number } | { kind: 'editor'; week: number; assignmentId: string; isNew?: boolean } | { kind: 'designer' };

  export let course: CourseShape;
  export let modules: ModuleShape[];
  export let view: View;

  const dispatch = createEventDispatcher<{
    selectCourse: void;
    selectModule: number;
    selectDesigner: void;
  }>();
</script>

<nav class="course-nav" aria-label="Course modules">
  <button
    class="course-nav__home"
    class:active={view.kind === 'course'}
    on:click={() => dispatch('selectCourse')}
    aria-current={view.kind === 'course' ? 'page' : undefined}
  >
    <span class="course-nav__code">{course.code}</span>
    <span class="course-nav__title">{course.title}</span>
  </button>

  <ol class="course-nav__modules" role="list">
    {#each modules as mod, i}
      <li
        in:fly={{ x: -12, duration: 320, delay: 60 + i * 50, easing: quintOut }}
      >
        <button
          class="course-nav__module"
          class:active={(view.kind === 'module' || view.kind === 'editor') && view.week === mod.week}
          on:click={() => dispatch('selectModule', mod.week)}
          aria-current={(view.kind === 'module' || view.kind === 'editor') && view.week === mod.week ? 'page' : undefined}
        >
          <span class="course-nav__week">W{mod.week}</span>
          <span class="course-nav__module-title">{mod.title}</span>
          <span
            class="course-nav__indicator"
            class:has-assignment={mod.assignments.length > 0}
            aria-label={mod.assignments.length > 0 ? 'has assignment' : 'no assignment yet'}
          ></span>
        </button>
      </li>
    {/each}
  </ol>

  <button
    class="course-nav__designer"
    class:active={view.kind === 'designer'}
    on:click={() => dispatch('selectDesigner')}
    aria-label="Learning designer view"
    title="Learning designer — bearings"
  >
    ⚙ designer
  </button>
</nav>

<style lang="scss">
  .course-nav {
    background: $color-bg-paper;
    border-right: 1px solid $color-border;
    border-top: $border-top;
    display: flex;
    flex-direction: column;
    padding: $space-lg 0;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
  }

  .course-nav__home {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
    padding: $space-sm $space-lg;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    border-left: 3px solid transparent;
    transition: border-color 240ms ease, background 240ms ease;
    margin-bottom: $space-lg;

    &:hover { background: $una-light-green; }

    &.active {
      border-left-color: $una-gold;
      background: $una-light-green;
    }
  }

  .course-nav__code {
    font-family: $font-mono;
    font-size: 0.68rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .course-nav__title {
    font-family: $font-serif;
    font-size: 0.88rem;
    color: $una-dark-1;
    line-height: 1.35;
  }

  .course-nav__modules {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
  }

  .course-nav__module {
    display: grid;
    grid-template-columns: 32px 1fr 14px;
    align-items: center;
    gap: $space-xs;
    width: 100%;
    padding: $space-sm $space-lg $space-sm $space-md;
    background: none;
    border: none;
    border-left: 3px solid transparent;
    cursor: pointer;
    text-align: left;
    transition: border-color 240ms ease, background 240ms ease;

    &:hover { background: $una-light-green; }

    &.active {
      border-left-color: $una-gold;
      background: $una-light-green;
    }
  }

  .course-nav__week {
    font-family: $font-mono;
    font-size: 0.68rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .course-nav__module-title {
    font-family: $font-sans;
    font-size: 0.82rem;
    color: $una-dark-1;
    line-height: 1.3;
  }

  .course-nav__designer {
    margin-top: auto;
    padding: $space-sm $space-lg;
    background: none;
    border: none;
    border-top: 1px solid $color-border;
    border-left: 3px solid transparent;
    cursor: pointer;
    text-align: left;
    font-family: $font-mono;
    font-size: 0.68rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    transition: border-color 240ms ease, background 240ms ease;
    width: 100%;

    &:hover { background: $una-light-green; }
    &.active {
      border-left-color: $una-gold;
      background: $una-light-green;
    }
  }

  .course-nav__indicator {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    border: 1px solid $color-border;
    background: transparent;
    transition: background 280ms ease, border-color 280ms ease;
    justify-self: center;

    &.has-assignment {
      background: $una-gold;
      border-color: $una-gold;
    }
  }
</style>
