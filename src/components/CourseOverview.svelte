<script lang="ts">
  import { fly } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';

  type OutcomeRow = { id: number; text: string; position: number };
  type CourseShape = {
    id: number;
    code: string;
    title: string;
    description: string;
    periodType: string;
    outcomes: string[];
    outcomeRows: OutcomeRow[];
  };

  export let course: CourseShape;
</script>

<article class="course-overview">
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

<style lang="scss">
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
</style>
