<script lang="ts">
  import { session, currentAssignment } from '../stores/session';
  import { courseContext } from '../stores/courseContext';
  import axios from 'axios';

  function handleModuleInput(e: Event) {
    const idx = $session.drawerIndex;
    const value = (e.target as HTMLInputElement).value;
    session.update(s => {
      const assignments = [...s.assignments];
      assignments[idx] = { ...assignments[idx], module: value };
      return { ...s, assignments };
    });
  }

  function close() {
    session.update(s => ({ ...s, drawerOpen: false }));
  }

  function prev() {
    session.update(s => ({ ...s, drawerIndex: Math.max(0, s.drawerIndex - 1) }));
  }

  function next() {
    session.update(s => ({
      ...s,
      drawerIndex: Math.min(s.assignments.length - 1, s.drawerIndex + 1),
    }));
  }

  async function exportToCanvas() {
    if (!$currentAssignment) return;

    session.update(s => ({
      ...s,
      canvasExporting: true,
      canvasExportError: null,
      canvasExportUrl: null,
    }));

    try {
      const res = await axios.post(
        '/api/canvas/assignment',
        {
          assignment: $currentAssignment,
          assignment_id: $currentAssignment.id,
          canvas_course_id: $courseContext.canvasCourseId,
        },
        { withCredentials: true }
      );
      session.update(s => ({
        ...s,
        canvasExporting: false,
        canvasExportUrl: res.data.html_url,
      }));
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.error ?? err.message)
        : err instanceof Error ? err.message : 'Canvas export failed';
      console.error('[canvas] exportToCanvas failed:', err);
      session.update(s => ({
        ...s,
        canvasExporting: false,
        canvasExportError: msg,
      }));
    }
  }
</script>

{#if $session.drawerOpen && $currentAssignment}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="drawer-backdrop" on:click={close} role="presentation"></div>

  <aside class="drawer" aria-label="Assignment draft">
    <div class="drawer__header">
      <h2 class="drawer__title">Assignment Draft</h2>
      <div class="drawer__header-right">
        {#if $session.assignments.length > 1}
          <div class="drawer__nav">
            <button on:click={prev} disabled={$session.drawerIndex === 0}>‹</button>
            <span>{$session.drawerIndex + 1} / {$session.assignments.length}</span>
            <button on:click={next} disabled={$session.drawerIndex === $session.assignments.length - 1}>›</button>
          </div>
        {/if}
        <button class="drawer__close" on:click={close} aria-label="Close drawer">✕</button>
      </div>
    </div>

    <div class="drawer__body">
      <section class="drawer__section">
        <h3 class="drawer__field-label">Title</h3>
        <p class="drawer__field-value drawer__field-value--title">{$currentAssignment.title}</p>
        <div class="drawer__module-row">
          <label class="drawer__module-label" for="module-input">Module / Week</label>
          <input
            id="module-input"
            class="drawer__module-input"
            type="text"
            placeholder="e.g. Week 3"
            value={$currentAssignment.module ?? ''}
            on:input={handleModuleInput}
          />
        </div>
      </section>

      <section class="drawer__section">
        <h3 class="drawer__field-label">Description</h3>
        <p class="drawer__field-value">{$currentAssignment.description}</p>
      </section>

      {#if $currentAssignment.aligned_outcomes?.length}
        <section class="drawer__section">
          <h3 class="drawer__field-label">Course Outcomes Addressed</h3>
          <ul class="drawer__list">
            {#each $currentAssignment.aligned_outcomes as outcome}
              <li>{outcome}</li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if $currentAssignment.learning_outcomes?.length}
        <section class="drawer__section">
          <h3 class="drawer__field-label">Assignment Outcomes</h3>
          <ul class="drawer__list">
            {#each $currentAssignment.learning_outcomes as outcome}
              <li>{outcome}</li>
            {/each}
          </ul>
        </section>
      {/if}

      <section class="drawer__section drawer__section--row">
        <div>
          <h3 class="drawer__field-label">Points</h3>
          <p class="drawer__field-value">{$currentAssignment.points_possible}</p>
        </div>
        <div>
          <h3 class="drawer__field-label">Submission</h3>
          <p class="drawer__field-value">{$currentAssignment.submission_types.join(', ')}</p>
        </div>
      </section>

      {#if $currentAssignment.rubric?.length}
        <section class="drawer__section">
          <h3 class="drawer__field-label">Rubric</h3>
          <div class="drawer__rubric">
            {#each $currentAssignment.rubric as row}
              <div class="drawer__criterion">
                <div class="drawer__criterion-header">
                  <span class="drawer__criterion-name">{row.criterion}</span>
                  <span class="drawer__criterion-points">{row.points} pts</span>
                </div>
                {#if row.long_description}
                  <p class="drawer__criterion-desc">{row.long_description}</p>
                {/if}
                {#if row.ratings?.length}
                  <div class="drawer__ratings">
                    {#each row.ratings as rating}
                      <div class="drawer__rating">
                        <span class="drawer__rating-label">{rating.description}</span>
                        <span class="drawer__rating-pts">{rating.points}</span>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </section>
      {/if}
    </div>

    <div class="drawer__footer">
      {#if $session.canvasExportUrl}
        <p class="drawer__export-success">
          ✓ Created in Canvas:
          <a href={$session.canvasExportUrl} target="_blank" rel="noreferrer">
            view assignment →
          </a>
        </p>
      {:else}
        {#if $session.canvasExportError}
          <p class="drawer__export-error">{$session.canvasExportError}</p>
        {/if}
        <button
          class="drawer__canvas-btn"
          on:click={exportToCanvas}
          disabled={$session.canvasExporting}
        >
          {$session.canvasExporting ? 'sending to Canvas…' : 'send to Canvas'}
        </button>
      {/if}
    </div>
  </aside>
{/if}

<style lang="scss">
  .drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba($una-dark-1, 0.3);
    z-index: 10;
  }

  .drawer {
    position: fixed;
    top: 0;
    right: 0;
    height: 100vh;
    width: $drawer-width;
    max-width: 100vw;
    background: $color-bg-paper;
    border-left: 1px solid $color-border;
    border-top: $border-top;
    z-index: 11;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 16px rgba($una-dark-1, 0.15);
  }

  .drawer__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $space-md $space-lg;
    border-bottom: 1px solid $color-border;
    flex-shrink: 0;
  }

  .drawer__header-right {
    display: flex;
    align-items: center;
    gap: $space-sm;
  }

  .drawer__nav {
    display: flex;
    align-items: center;
    gap: $space-xs;
    font-family: $font-sans;
    font-size: 0.8rem;
    color: $una-mid-green;

    button {
      background: none;
      border: 1px solid $color-border;
      width: 24px;
      height: 24px;
      cursor: pointer;
      font-size: 1rem;
      line-height: 1;
      color: $una-mid-green;

      &:hover:not(:disabled) { border-color: $una-gold; color: $una-dark-1; }
      &:disabled { opacity: 0.3; cursor: not-allowed; }
    }
  }

  .drawer__title {
    font-family: $font-serif;
    font-size: 1.15rem;
    font-weight: normal;
    margin: 0;
    color: $una-dark-1;
  }

  .drawer__close {
    background: none;
    border: none;
    font-size: 1.1rem;
    cursor: pointer;
    color: $una-mid-green;
    padding: $space-xs;

    &:hover { color: $una-dark-1; }
  }

  .drawer__body {
    flex: 1;
    overflow-y: auto;
    padding: $space-md $space-lg;
    display: flex;
    flex-direction: column;
    gap: $space-md;
  }

  .drawer__section {
    padding-bottom: $space-md;
    border-bottom: 1px solid $color-border;

    &:last-child { border-bottom: none; }

    &--row {
      display: flex;
      gap: $space-xl;
    }
  }

  .drawer__field-label {
    font-family: $font-sans;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: $una-mid-green;
    margin: 0 0 $space-xs;
  }

  .drawer__field-value {
    font-family: $font-serif;
    margin: 0;
    line-height: 1.6;

    &--title {
      font-size: 1.05rem;
      font-weight: bold;
    }
  }

  .drawer__module-row {
    display: flex;
    align-items: center;
    gap: $space-sm;
    margin-top: $space-sm;
  }

  .drawer__module-label {
    font-family: $font-sans;
    font-size: 0.75rem;
    color: $una-mid-green;
    white-space: nowrap;
  }

  .drawer__module-input {
    font-family: $font-sans;
    font-size: 0.85rem;
    padding: 2px $space-sm;
    border: 1px solid $color-border;
    background: white;
    color: $color-text;
    width: 120px;

    &:focus { outline: 2px solid $una-gold; outline-offset: 1px; }
  }

  .drawer__list {
    font-family: $font-serif;
    margin: 0;
    padding-left: $space-lg;
    line-height: 1.8;
  }

  .drawer__rubric {
    display: flex;
    flex-direction: column;
    gap: $space-sm;
  }

  .drawer__criterion {
    border: 1px solid $color-border;
    padding: $space-sm;
  }

  .drawer__criterion-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: $space-xs;
  }

  .drawer__criterion-name {
    font-family: $font-sans;
    font-size: 0.85rem;
    font-weight: 600;
    color: $una-dark-1;
  }

  .drawer__criterion-points {
    font-family: $font-sans;
    font-size: 0.75rem;
    color: $una-mid-green;
  }

  .drawer__criterion-desc {
    font-family: $font-serif;
    font-size: 0.85rem;
    margin: 0 0 $space-xs;
    color: $una-dark-2;
    line-height: 1.5;
  }

  .drawer__ratings {
    display: flex;
    gap: $space-xs;
    flex-wrap: wrap;
  }

  .drawer__rating {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: $una-light-green;
    padding: 2px $space-sm;
    font-family: $font-sans;
    font-size: 0.72rem;
  }

  .drawer__rating-label { color: $una-mid-green; }
  .drawer__rating-pts { font-weight: 600; color: $una-dark-1; }

  .drawer__footer {
    flex-shrink: 0;
    padding: $space-md $space-lg;
    border-top: 1px solid $color-border;
  }

  .drawer__canvas-btn {
    width: 100%;
    background: $una-gold;
    color: $una-dark-1;
    border: none;
    padding: $space-sm $space-lg;
    font-family: $font-sans;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    letter-spacing: 0.04em;

    &:hover:not(:disabled) { background: darken($una-gold, 8%); }
    &:disabled { opacity: 0.6; cursor: not-allowed; }
  }

  .drawer__export-success {
    font-family: $font-serif;
    color: $una-mid-green;
    margin: 0 0 $space-sm;
    a { color: $una-mid-green; }
  }

  .drawer__export-error {
    font-size: 0.85rem;
    color: #c00;
    margin: 0 0 $space-sm;
  }
</style>
