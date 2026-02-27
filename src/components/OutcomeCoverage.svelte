<script lang="ts">
  import { derived } from 'svelte/store';
  import { session } from '../stores/session';
  import { courseContext } from '../stores/courseContext';

  let open = false;

  // Parse learning outcomes: split on newlines, filter blanks
  const outcomes = derived(courseContext, $ctx =>
    ($ctx.learningOutcomes || '')
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean)
  );

  type CoverageRow = {
    outcome: string;
    assignments: string[];   // assignment titles that address this outcome
  };

  function normalize(s: string): string {
    return s.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();
  }

  const coverage = derived([outcomes, session], ([$outcomes, $session]) => {
    return $outcomes.map(outcome => {
      const norm = normalize(outcome);
      const matching = $session.assignments
        .filter(a =>
          (a.aligned_outcomes ?? []).some(ao => {
            const normAo = normalize(ao);
            // Match if either contains the other (handles paraphrase)
            return normAo.includes(norm.slice(0, 30)) || norm.includes(normAo.slice(0, 30));
          })
        )
        .map(a => a.title);
      return { outcome, assignments: matching } as CoverageRow;
    });
  });

  $: covered = $coverage.filter(r => r.assignments.length > 0).length;
  $: total = $coverage.length;
  $: pct = total > 0 ? Math.round((covered / total) * 100) : 0;
</script>

{#if $outcomes.length > 0 && $session.assignments.length > 0}
  <div class="coverage">
    <button
      class="coverage__toggle"
      on:click={() => open = !open}
      aria-expanded={open}
    >
      <span class="coverage__toggle-label">outcome coverage</span>
      <span class="coverage__toggle-stat">
        {covered} / {total} addressed ({pct}%)
      </span>
      <span class="coverage__toggle-arrow">{open ? '▲' : '▼'}</span>
    </button>

    {#if open}
      <div class="coverage__body">
        {#each $coverage as row}
          <div class="coverage__row coverage__row--{row.assignments.length > 0 ? 'covered' : 'gap'}">
            <div class="coverage__indicator" aria-hidden="true">
              {row.assignments.length > 0 ? '●' : '○'}
            </div>
            <div class="coverage__content">
              <p class="coverage__outcome">{row.outcome}</p>
              {#if row.assignments.length > 0}
                <ul class="coverage__assignments">
                  {#each row.assignments as title}
                    <li>{title}</li>
                  {/each}
                </ul>
              {:else}
                <p class="coverage__gap-label">not yet addressed</p>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style lang="scss">
  .coverage {
    margin-top: $space-lg;
    border: 1px solid $color-border;
    background: $color-bg-paper;
  }

  .coverage__toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: $space-sm;
    padding: $space-sm $space-md;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;

    &:hover {
      background: $una-light-green;
    }
  }

  .coverage__toggle-label {
    font-family: $font-sans;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: $una-mid-green;
    flex: 1;
  }

  .coverage__toggle-stat {
    font-family: $font-sans;
    font-size: 0.78rem;
    color: $una-mid-green;
  }

  .coverage__toggle-arrow {
    font-size: 0.65rem;
    color: $una-mid-green;
  }

  .coverage__body {
    border-top: 1px solid $color-border;
    padding: $space-sm 0;
  }

  .coverage__row {
    display: flex;
    gap: $space-sm;
    padding: $space-xs $space-md;
    align-items: flex-start;

    &--gap {
      opacity: 0.6;
    }
  }

  .coverage__indicator {
    font-size: 0.75rem;
    padding-top: 3px;
    flex-shrink: 0;
    color: $una-gold;

    .coverage__row--gap & {
      color: $una-mid-green;
    }
  }

  .coverage__content {
    flex: 1;
  }

  .coverage__outcome {
    font-family: $font-serif;
    font-size: 0.85rem;
    margin: 0 0 2px;
    line-height: 1.4;
    color: $una-dark-1;
  }

  .coverage__assignments {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;

    li {
      font-family: $font-sans;
      font-size: 0.72rem;
      color: $una-dark-2;
      background: $una-light-green;
      padding: 1px $space-sm;
      border: 1px solid $color-border;
    }
  }

  .coverage__gap-label {
    font-family: $font-sans;
    font-size: 0.72rem;
    color: $una-mid-green;
    font-style: italic;
    margin: 0;
  }
</style>
