<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import axios from 'axios';
  import CourseNav from './CourseNav.svelte';
  import CourseOverview from './CourseOverview.svelte';
  import ModuleView from './ModuleView.svelte';
  import ThreadSidebar from './ThreadSidebar.svelte';
  import { sidebarOpen } from '../stores/threads';

  type OutcomeRow = { id: number; text: string; position: number };
  type AssignmentSnapshot = { id: number; label: string | null; description: string };
  type AssignmentStub = { id: string; title: string; module_label: string; position: number | null; snapshot: AssignmentSnapshot | null };
  type CourseShape = {
    id: number;
    code: string;
    title: string;
    description: string;
    periodType: string;
    outcomes: string[];
    outcomeRows: OutcomeRow[];
  };
  type ModuleShape = {
    id: number;
    week: number;
    title: string;
    description: string;
    outcomeIds: number[];
    assignments: AssignmentStub[];
  };
  type View = { kind: 'course' } | { kind: 'module'; week: number };

  let course: CourseShape | null = null;
  let modules: ModuleShape[] = [];
  let loading = true;
  let fetchError = '';

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

      const pt = course.periodType;
      const [modRes, asgRes] = await Promise.all([
        axios.get(`/api/modules?course_id=${c.id}`, { withCredentials: true }),
        axios.get(`/api/assignments?course_id=${c.id}`, { withCredentials: true }),
      ]);

      const saved: AssignmentStub[] = asgRes.data.assignments ?? [];
      modules = (modRes.data.modules ?? []).map((m: any, i: number) => ({
        id: m.id,
        week: m.position + 1,
        title: m.title,
        description: m.description,
        outcomeIds: m.outcomeIds ?? [],
        assignments: saved.filter(a => a.module_label === `${pt} ${m.position + 1}`),
      }));
    } catch (e) {
      fetchError = 'Could not load course data.';
      console.error('[CourseMap] fetch error:', e);
    } finally {
      loading = false;
    }
  });

  let view: View = { kind: 'course' };

  function selectModule(week: number) {
    view = { kind: 'module', week };
  }

  function selectCourse() {
    view = { kind: 'course' };
  }

  $: gridCols = $sidebarOpen ? '260px 1fr 320px' : '260px 1fr';

  $: activeModule = view.kind === 'module'
    ? modules.find(m => view.kind === 'module' && m.week === view.week) ?? null
    : null;

  $: activeOutcomes = (activeModule && course)
    ? activeModule.outcomeIds
        .map(id => course!.outcomeRows.find(lo => lo.id === id))
        .filter((lo): lo is OutcomeRow => !!lo)
    : [];

  function handleAssignmentSaved(event: CustomEvent<AssignmentStub>) {
    if (!activeModule) return;
    const saved = event.detail;
    const week = activeModule.week;
    modules = modules.map(m => {
      if (m.week !== week) return m;
      const exists = m.assignments.some(a => a.id === saved.id);
      const assignments = exists
        ? m.assignments.map(a => a.id === saved.id ? saved : a)
        : [...m.assignments, saved];
      return { ...m, assignments };
    });
  }

  function handleAssignmentsReordered(event: CustomEvent<{ week: number; assignments: AssignmentStub[] }>) {
    modules = modules.map(m =>
      m.week === event.detail.week ? { ...m, assignments: event.detail.assignments } : m
    );
  }
</script>

{#if loading}
  <div class="course-loading" aria-live="polite">loading…</div>
{:else if fetchError}
  <div class="course-error" role="alert">{fetchError}</div>
{:else if course}

<div class="course-layout" style="grid-template-columns: {gridCols}">
  <CourseNav
    {course}
    {modules}
    {view}
    on:selectCourse={selectCourse}
    on:selectModule={(e) => selectModule(e.detail)}
  />

  <main class="course-main">
    <div class="course-main__viewport">
      {#if view.kind === 'course'}
        <div in:fade={{ duration: 320, delay: 80 }}>
          <CourseOverview {course} />
        </div>
      {:else if view.kind === 'module' && activeModule}
        <ModuleView
          {activeModule}
          {activeOutcomes}
          {course}
          on:assignmentSaved={handleAssignmentSaved}
          on:assignmentsReordered={handleAssignmentsReordered}
        />
      {/if}
    </div>
  </main>

  {#if $sidebarOpen}
    <ThreadSidebar />
  {/if}
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

  .course-main {
    padding: $space-xl $space-xl $space-xl;
    max-width: 700px;
    overflow: hidden;
  }

  .course-main__viewport {
    position: relative;
  }
</style>
