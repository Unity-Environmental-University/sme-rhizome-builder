<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import axios from 'axios';
  import CourseNav from './CourseNav.svelte';
  import CourseOverview from './CourseOverview.svelte';
  import ModuleView from './ModuleView.svelte';
  import AssignmentPane from './AssignmentPane.svelte';
  import ThreadSidebar from './ThreadSidebar.svelte';
  import DesignerView from './DesignerView.svelte';
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
  type View =
    | { kind: 'course' }
    | { kind: 'module'; week: number }
    | { kind: 'editor'; week: number; assignmentId: string; isNew?: boolean }
    | { kind: 'designer' };

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

  function selectDesigner() {
    view = { kind: 'designer' };
  }

  $: gridCols = $sidebarOpen ? '260px 1fr 320px' : '260px 1fr';

  function getViewWeek(v: View): number | null {
    if (v.kind === 'module' || v.kind === 'editor') return v.week;
    return null;
  }

  $: viewWeek = getViewWeek(view);
  $: activeModule = viewWeek !== null
    ? modules.find(m => m.week === viewWeek) ?? null
    : null;

  $: activeOutcomes = (activeModule && course)
    ? activeModule.outcomeIds
        .map(id => course!.outcomeRows.find(lo => lo.id === id))
        .filter((lo): lo is OutcomeRow => !!lo)
    : [];

  function openAssignment(week: number, assignmentId: string) {
    view = { kind: 'editor', week, assignmentId };
  }

  function newAssignment(week: number) {
    view = { kind: 'editor', week, assignmentId: '', isNew: true };
  }

  function handleEditorSaved(event: CustomEvent<{ id: string; title: string; module_label: string }>) {
    const { id, title, module_label } = event.detail;
    modules = modules.map(m => {
      const ml = `${course!.periodType} ${m.week}`;
      if (ml !== module_label) return m;
      const exists = m.assignments.some(a => a.id === id);
      if (exists) {
        return { ...m, assignments: m.assignments.map(a => a.id === id ? { ...a, title } : a) };
      }
      return { ...m, assignments: [...m.assignments, { id, title, module_label, position: null, snapshot: null }] };
    });
    // Update the view to use the real ID if this was a new assignment
    if (view.kind === 'editor' && !view.assignmentId) {
      view = { kind: 'editor', week: view.week, assignmentId: id };
    }
  }

  function handleEditorBack() {
    if (view.kind === 'editor') {
      view = { kind: 'module', week: view.week };
    }
  }

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
    on:selectDesigner={selectDesigner}
  />

  <main class="course-main" class:editor-active={view.kind === 'editor'}>
    {#if view.kind === 'course'}
      <div class="course-main__viewport" in:fade={{ duration: 320, delay: 80 }}>
        <CourseOverview {course} />
      </div>
    {:else if view.kind === 'module' && activeModule}
      <div class="course-main__viewport">
        <ModuleView
          {activeModule}
          {activeOutcomes}
          {course}
          on:openAssignment={(e) => openAssignment(activeModule.week, e.detail.assignmentId)}
          on:newAssignment={() => newAssignment(activeModule.week)}
          on:assignmentsReordered={handleAssignmentsReordered}
        />
      </div>
    {:else if view.kind === 'designer'}
      <div class="course-main__viewport" in:fade={{ duration: 200 }}>
        <DesignerView {course} />
      </div>
    {:else if view.kind === 'editor'}
      <AssignmentPane
        assignmentId={view.assignmentId || null}
        moduleLabel="{course.periodType} {view.week}"
        {course}
        alignedOutcomes={activeOutcomes}
        on:saved={handleEditorSaved}
        on:back={handleEditorBack}
      />
    {/if}
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
    padding: $space-xl;
    max-width: 700px;
    overflow: hidden;

    &.editor-active {
      padding: 0;
      max-width: none;
    }
  }

  .course-main__viewport {
    position: relative;
  }
</style>
