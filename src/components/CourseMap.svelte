<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';
  import axios from 'axios';
  import AssignmentEditor from './AssignmentEditor.svelte';

  type OutcomeRow = { id: number; text: string; position: number };
  type AssignmentStub = { id: string; title: string; module_label: string; position: number | null };
  type CourseShape = {
    id: number;
    code: string;
    title: string;
    description: string;
    periodType: string;
    outcomes: string[];
    outcomeRows: OutcomeRow[];
  };

  let course: CourseShape | null = null;
  let loading = true;
  let fetchError = '';

  // Module shape — assignments loaded from API after mount
  type ModuleShape = {
    week: number;
    title: string;
    description: string;
    outcomeIndices: number[];
    assignments: AssignmentStub[];
  };

  let modules: ModuleShape[] = [
    {
      week: 1,
      title: 'Foundations of Coral Biology',
      description: 'The architecture of a reef. Polyp biology, symbiosis with zooxanthellae, calcification. What a healthy system looks like before anything goes wrong.',
      outcomeIndices: [0],
      assignments: [],
    },
    {
      week: 2,
      title: 'Bleaching Mechanisms',
      description: 'Thermal stress, oxidative damage, the breakdown of the coral-algae partnership. What is actually happening inside the animal when a reef turns white.',
      outcomeIndices: [0, 1],
      assignments: [],
    },
    {
      week: 3,
      title: 'Stressors and Monitoring',
      description: 'Local and global pressures acting in concert. How to read a reef — what field data and remote sensing can and cannot tell you about where a system is headed.',
      outcomeIndices: [1, 3],
      assignments: [],
    },
    {
      week: 4,
      title: 'Restoration Strategies',
      description: 'Coral gardening, assisted gene flow, substrate work. The tradeoffs between intervention and letting systems find their own way. What works, where, and under what conditions.',
      outcomeIndices: [2],
      assignments: [],
    },
    {
      week: 5,
      title: 'Social and Political Dimensions',
      description: 'A reef does not exist outside of the people who live near it, fish from it, dive on it, govern it. Conservation decisions are political decisions. This week asks students to sit with that.',
      outcomeIndices: [4],
      assignments: [],
    },
  ];

  onMount(async () => {
    try {
      const res = await axios.get('/api/courses', { withCredentials: true });
      const courses = res.data.courses;
      if (!courses.length) {
        fetchError = 'No courses found.';
        return;
      }
      const c = courses[0];
      const outcomeRows: OutcomeRow[] = c.learningOutcomeRows ?? [];
      const outcomes: string[] = outcomeRows.length
        ? outcomeRows.map((lo: OutcomeRow) => lo.text)
        : (c.learningOutcomes ?? '').split('\n').filter(Boolean);

      course = {
        id: c.id,
        code: c.courseCode,
        title: c.courseTitle,
        description: '',
        periodType: c.periodType ?? 'Week',
        outcomes,
        outcomeRows,
      };

      // Load saved assignments and distribute into modules by module_label
      const pt = course.periodType;
      const asgRes = await axios.get(`/api/assignments?course_id=${c.id}`, { withCredentials: true });
      const saved: AssignmentStub[] = asgRes.data.assignments ?? [];
      modules = modules.map(mod => ({
        ...mod,
        assignments: saved.filter(a => a.module_label === `${pt} ${mod.week}`),
      }));
    } catch (e) {
      fetchError = 'Could not load course data.';
      console.error('[CourseMap] fetch error:', e);
    } finally {
      loading = false;
    }
  });

  type View = { kind: 'course' } | { kind: 'module'; week: number };

  let view: View = { kind: 'course' };
  let prevView: View = { kind: 'course' };
  let editorOpen = false;
  let editorContent = '';
  let assignmentTitle = '';
  let saving = false;

  function selectModule(week: number) {
    editorOpen = false;
    prevView = view;
    view = { kind: 'module', week };
  }

  function selectCourse() {
    editorOpen = false;
    prevView = view;
    view = { kind: 'course' };
  }

  // Direction: going into a module slides right; going back to course slides left
  $: direction = view.kind === 'module' ? 1 : -1;

  $: activeModule = view.kind === 'module'
    ? modules.find(m => view.kind === 'module' && m.week === view.week)
    : null;

  $: activeOutcomes = (activeModule && course)
    ? activeModule.outcomeIndices
        .map(i => course!.outcomeRows[i])
        .filter((lo): lo is OutcomeRow => !!lo)
    : [];

  async function saveAssignment() {
    if (!course || !activeModule || saving) return;
    saving = true;
    try {
      const res = await axios.post('/api/assignments', {
        course_id: course.id,
        title: assignmentTitle.trim() || 'Untitled',
        description: editorContent,
        module_label: `${course.periodType} ${activeModule.week}`,
        aligned_outcome_ids: activeOutcomes.map(o => o.id),
      }, { withCredentials: true });

      const saved = res.data as AssignmentStub;
      // Add to this module's list
      modules = modules.map(m =>
        m.week === activeModule!.week
          ? { ...m, assignments: [...m.assignments, saved] }
          : m
      );
      editorOpen = false;
      assignmentTitle = '';
      editorContent = '';
    } catch (e) {
      console.error('[CourseMap] save failed:', e);
    } finally {
      saving = false;
    }
  }

  function moveUp(week: number, index: number) { moveAssignment(week, index, -1); }
  function moveDown(week: number, index: number) { moveAssignment(week, index, 1); }

  async function moveAssignment(week: number, index: number, direction: -1 | 1) {
    const mod = modules.find(m => m.week === week);
    if (!mod) return;
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= mod.assignments.length) return;

    // Swap locally first for immediate feedback
    const list = [...mod.assignments];
    [list[index], list[newIndex]] = [list[newIndex], list[index]];
    modules = modules.map(m => m.week === week ? { ...m, assignments: list } : m);

    // Persist new positions
    try {
      await Promise.all(list.map((a, i) =>
        axios.patch(`/api/assignments/${a.id}`, { position: i }, { withCredentials: true })
      ));
    } catch (e) {
      console.error('[CourseMap] reorder failed:', e);
    }
  }
</script>

{#if loading}
  <div class="course-loading" aria-live="polite">loading…</div>
{:else if fetchError}
  <div class="course-error" role="alert">{fetchError}</div>
{:else if course}

<div class="course-layout">

  <nav class="course-nav" aria-label="Course modules">
    <button
      class="course-nav__home"
      class:active={view.kind === 'course'}
      on:click={selectCourse}
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
            class:active={view.kind === 'module' && view.week === mod.week}
            on:click={() => selectModule(mod.week)}
            aria-current={view.kind === 'module' && view.week === mod.week ? 'page' : undefined}
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
  </nav>

  <main class="course-main">
    <div class="course-main__viewport">

    {#if view.kind === 'course'}
      <article
        class="course-overview"
        in:fade={{ duration: 320, delay: 80 }}
      >
        <header class="course-overview__header">
          <p class="course-overview__code">{course.code}</p>
          <h1 class="course-overview__title">{course.title}</h1>
        </header>

        <section class="course-overview__section" aria-labelledby="desc-heading">
          <h2 id="desc-heading" class="course-overview__section-title">Description</h2>
          <p
            class="course-overview__description"
            in:fly={{ y: 10, duration: 340, delay: 80, easing: quintOut }}
          >{course.description}</p>
        </section>

        <section class="course-overview__section" aria-labelledby="outcomes-heading">
          <h2 id="outcomes-heading" class="course-overview__section-title">Learning outcomes</h2>
          <ol class="course-overview__outcomes">
            {#each course.outcomes as outcome, i}
              <li
                class="course-overview__outcome"
                in:fly={{ y: 12, duration: 360, delay: 120 + i * 70, easing: quintOut }}
              >
                {outcome}
              </li>
            {/each}
          </ol>
        </section>
      </article>

    {:else if view.kind === 'module' && activeModule}
      <article
        class="module-view"
        in:fade={{ duration: 320, delay: 80 }}
      >
        <header class="module-view__header">
          <p class="module-view__week">Week {activeModule.week}</p>
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
                  <span class="module-view__assignment-name">{a.title}</span>
                  <span class="module-view__draft">draft</span>
                  {#if activeModule}
                  <span class="module-view__reorder" aria-label="Reorder">
                    <button
                      class="module-view__reorder-btn"
                      on:click={() => moveUp(activeModule.week, i)}
                      disabled={i === 0}
                      aria-label="Move up"
                    >↑</button>
                    <button
                      class="module-view__reorder-btn"
                      on:click={() => moveDown(activeModule.week, i)}
                      disabled={i === activeModule.assignments.length - 1}
                      aria-label="Move down"
                    >↓</button>
                  </span>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}

          {#if !editorOpen}
            <button
              class="module-view__add"
              on:click={() => { editorOpen = true; }}
              in:fade={{ duration: 280, delay: 200 }}
            >
              + add assignment
            </button>
          {/if}
        </section>

        {#if editorOpen}
          <section
            class="module-view__editor"
            aria-label="New assignment editor"
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
                on:click={() => { editorOpen = false; assignmentTitle = ''; editorContent = ''; }}
                aria-label="Close editor"
              >✕</button>
            </header>

            <AssignmentEditor
              placeholder="What will students do in week {activeModule.week}?"
              onUpdate={(html) => { editorContent = html; }}
            />

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
    {/if}

    </div>
  </main>
</div>

{/if}

<style lang="scss">
  .course-loading,
  .course-error {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    font-family: $font-sans;
    font-size: 0.85rem;
    color: $una-mid-green;
  }

  .course-error {
    color: $color-text;
  }

  .course-layout {
    display: grid;
    grid-template-columns: 260px 1fr;
    min-height: 100vh;
    background: $color-bg-body;
  }

  // ── Sidebar nav ────────────────────────────────────────────────

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

  // ── Main ───────────────────────────────────────────────────────

  .course-main {
    padding: $space-xl $space-xl $space-xl;
    max-width: 700px;
    overflow: hidden;
  }

  .course-main__viewport {
    position: relative;
  }

  // ── Course overview ────────────────────────────────────────────

  .course-overview__header {
    margin-bottom: $space-xl;
    border-top: $border-top;
    padding-top: $space-md;
  }

  .course-overview__code {
    font-family: $font-mono;
    font-size: 0.72rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 $space-xs;
  }

  .course-overview__title {
    font-family: $font-serif;
    font-size: 1.9rem;
    font-weight: normal;
    color: $una-dark-1;
    margin: 0;
    line-height: 1.2;
  }

  .course-overview__section {
    margin-bottom: $space-xl;
  }

  .course-overview__section-title {
    font-family: $font-sans;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: $una-mid-green;
    margin: 0 0 $space-md;
  }

  .course-overview__description {
    font-family: $font-serif;
    font-size: 1rem;
    line-height: 1.8;
    color: $color-text;
    white-space: pre-line;
    margin: 0;
  }

  .course-overview__outcomes {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: $space-lg;
    counter-reset: outcomes;
  }

  .course-overview__outcome {
    font-family: $font-serif;
    font-size: 0.95rem;
    line-height: 1.7;
    color: $color-text;
    display: grid;
    grid-template-columns: 28px 1fr;
    counter-increment: outcomes;

    &::before {
      content: counter(outcomes);
      font-family: $font-mono;
      font-size: 0.68rem;
      color: $una-mid-green;
      padding-top: 4px;
    }
  }

  // ── Module view ────────────────────────────────────────────────

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
