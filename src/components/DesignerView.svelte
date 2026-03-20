<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import axios from 'axios';

  type Statement = { id: number; text: string; observed: boolean | null };
  type Bearing = {
    id: number;
    text: string;
    weight: number;
    likelihood: number;
    statements: Statement[];
    _editing?: boolean;
  };

  type CourseShape = { id: number; code: string; title: string };

  export let course: CourseShape;

  let bearings: Bearing[] = [];
  let loading = true;
  let error = '';

  let newText = '';
  let newWeight = 0.5;
  let saving = false;

  onMount(async () => {
    await loadBearings();
  });

  async function loadBearings() {
    try {
      const res = await axios.get(`/api/bearings?course_id=${course.id}`, { withCredentials: true });
      bearings = (res.data as Bearing[]).map(b => ({ ...b, _editing: false }));
    } catch (e) {
      error = 'Could not load bearings.';
    } finally {
      loading = false;
    }
  }

  async function addBearing() {
    if (!newText.trim()) return;
    saving = true;
    try {
      const res = await axios.post('/api/bearings', {
        course_id: course.id,
        text: newText.trim(),
        weight: newWeight,
        likelihood: 0.5,
      }, { withCredentials: true });
      bearings = [...bearings, { ...res.data, _editing: false }];
      newText = '';
      newWeight = 0.5;
    } finally {
      saving = false;
    }
  }

  async function updateBearing(b: Bearing) {
    const res = await axios.patch(`/api/bearings/${b.id}`, {
      text: b.text,
      weight: b.weight,
      likelihood: b.likelihood,
    }, { withCredentials: true });
    bearings = bearings.map(x => x.id === b.id ? { ...res.data, statements: b.statements, _editing: false } : x);
  }

  async function deleteBearing(id: number) {
    await axios.delete(`/api/bearings/${id}`, { withCredentials: true });
    bearings = bearings.filter(b => b.id !== id);
  }

  async function addStatement(b: Bearing, text: string) {
    if (!text.trim()) return;
    const res = await axios.post(`/api/bearings/${b.id}/statements`, { text: text.trim() }, { withCredentials: true });
    bearings = bearings.map(x =>
      x.id === b.id ? { ...x, statements: [...x.statements, res.data] } : x
    );
  }

  function weightLabel(w: number): string {
    if (w >= 0.8) return 'strong pull toward';
    if (w >= 0.3) return 'pull toward';
    if (w >= -0.3) return 'neutral';
    if (w >= -0.8) return 'pull away from';
    return 'strong pull away from';
  }

  function evalRead(statements: Statement[]): { confirmed: number; disconfirmed: number; total: number; ratio: number } | null {
    const evaluated = statements.filter(s => s.observed !== null);
    if (!evaluated.length) return null;
    const confirmed = evaluated.filter(s => s.observed === true).length;
    const disconfirmed = evaluated.filter(s => s.observed === false).length;
    return { confirmed, disconfirmed, total: evaluated.length, ratio: confirmed / evaluated.length };
  }

  let newStatementTexts: Record<number, string> = {};
</script>

<div class="designer-view" in:fade={{ duration: 200 }}>
  <header class="designer-view__header">
    <p class="designer-view__eyebrow">Learning Designer</p>
    <h1 class="designer-view__title">Bearings — {course.code}</h1>
    <p class="designer-view__caption">
      Bearings are navigational directions, not destinations.
      They tell the AI what territory matters — not where to steer.
    </p>
  </header>

  {#if loading}
    <p class="designer-view__empty">loading…</p>
  {:else if error}
    <p class="designer-view__error">{error}</p>
  {:else}
    <ul class="bearings-list" role="list">
      {#each bearings as b (b.id)}
        <li class="bearing-card">
          {#if b._editing}
            <div class="bearing-card__edit">
              <textarea
                class="bearing-card__text-input"
                bind:value={b.text}
                rows="2"
              ></textarea>
              <label class="bearing-card__weight-label">
                <span>Weight: {b.weight >= 0 ? '+' : ''}{b.weight.toFixed(2)} — {weightLabel(b.weight)}</span>
                <input
                  type="range"
                  min="-1" max="1" step="0.05"
                  bind:value={b.weight}
                  class="bearing-card__slider"
                />
              </label>
              <div class="bearing-card__actions">
                <button class="btn-save" on:click={() => updateBearing(b)}>save</button>
                <button class="btn-cancel" on:click={() => { b._editing = false; bearings = bearings; }}>cancel</button>
              </div>
            </div>
          {:else}
            <div class="bearing-card__view">
              <p class="bearing-card__text">{b.text}</p>
              <span class="bearing-card__weight">{weightLabel(b.weight)}</span>
              {#each [evalRead(b.statements)].filter(r => r !== null) as read}
                <div class="bearing-card__read">
                  <div class="bearing-read__bar">
                    <div class="bearing-read__fill" style="width: {read.ratio * 100}%"></div>
                  </div>
                  <span class="bearing-read__label">{read.confirmed}/{read.total} confirmed</span>
                </div>
              {/each}
              <div class="bearing-card__row-actions">
                <button class="btn-text" on:click={() => { b._editing = true; bearings = bearings; }}>edit</button>
                <button class="btn-text btn-text--danger" on:click={() => deleteBearing(b.id)}>remove</button>
              </div>
            </div>
          {/if}

          {#if b.statements.length > 0}
            <ul class="statements-list" role="list">
              {#each b.statements as s (s.id)}
                <li class="statement" class:observed={s.observed === true} class:not-observed={s.observed === false}>
                  <span class="statement__indicator">{s.observed === true ? '✓' : s.observed === false ? '✗' : '·'}</span>
                  <span class="statement__text">{s.text}</span>
                </li>
              {/each}
            </ul>
          {/if}

          <div class="bearing-card__add-statement">
            <input
              class="statement-input"
              type="text"
              placeholder="add observable statement…"
              bind:value={newStatementTexts[b.id]}
              on:keydown={(e) => {
                if (e.key === 'Enter') {
                  addStatement(b, newStatementTexts[b.id] ?? '');
                  newStatementTexts[b.id] = '';
                }
              }}
            />
          </div>
        </li>
      {/each}
    </ul>

    {#if bearings.length === 0}
      <p class="designer-view__empty">No bearings set yet. Add the first one below.</p>
    {/if}

    <form class="add-bearing" on:submit|preventDefault={addBearing}>
      <h2 class="add-bearing__heading">New bearing</h2>
      <textarea
        class="add-bearing__text"
        bind:value={newText}
        placeholder="Describe the direction that matters for this course…"
        rows="2"
      ></textarea>
      <label class="add-bearing__weight-label">
        <span>Weight: {newWeight >= 0 ? '+' : ''}{newWeight.toFixed(2)} — {weightLabel(newWeight)}</span>
        <input
          type="range"
          min="-1" max="1" step="0.05"
          bind:value={newWeight}
          class="add-bearing__slider"
        />
      </label>
      <button class="btn-primary" type="submit" disabled={saving || !newText.trim()}>
        {saving ? 'adding…' : 'add bearing'}
      </button>
    </form>
  {/if}
</div>

<style lang="scss">
  .designer-view {
    padding: $space-xl;
    max-width: 640px;
  }

  .designer-view__header {
    margin-bottom: $space-xl;
  }

  .designer-view__eyebrow {
    font-family: $font-mono;
    font-size: 0.68rem;
    color: $una-mid-green;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 $space-xs;
  }

  .designer-view__title {
    font-family: $font-serif;
    font-size: 1.4rem;
    color: $una-dark-1;
    margin: 0 0 $space-sm;
  }

  .designer-view__caption {
    font-family: $font-sans;
    font-size: 0.82rem;
    color: $una-mid-green;
    margin: 0;
    line-height: 1.5;
  }

  .designer-view__empty {
    font-family: $font-sans;
    font-size: 0.82rem;
    color: $una-mid-green;
    font-style: italic;
  }

  .designer-view__error {
    color: #c0392b;
    font-size: 0.82rem;
  }

  .bearings-list {
    list-style: none;
    margin: 0 0 $space-xl;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: $space-md;
  }

  .bearing-card {
    background: $color-bg-paper;
    border: 1px solid $color-border;
    border-radius: 4px;
    padding: $space-md;

    &__view {
      display: flex;
      flex-direction: column;
      gap: $space-xs;
    }

    &__text {
      font-family: $font-sans;
      font-size: 0.9rem;
      color: $una-dark-1;
      margin: 0;
      line-height: 1.45;
    }

    &__weight {
      font-family: $font-mono;
      font-size: 0.68rem;
      color: $una-mid-green;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    &__read {
      display: flex;
      align-items: center;
      gap: $space-sm;
      margin-top: $space-xs;
    }

    &__row-actions {
      display: flex;
      gap: $space-sm;
      margin-top: $space-xs;
    }

    &__text-input {
      width: 100%;
      font-family: $font-sans;
      font-size: 0.9rem;
      border: 1px solid $color-border;
      border-radius: 3px;
      padding: $space-xs $space-sm;
      resize: vertical;
      margin-bottom: $space-sm;
    }

    &__weight-label {
      display: flex;
      flex-direction: column;
      gap: $space-xs;
      font-family: $font-mono;
      font-size: 0.68rem;
      color: $una-mid-green;
      margin-bottom: $space-sm;
    }

    &__slider {
      width: 100%;
    }

    &__actions {
      display: flex;
      gap: $space-sm;
    }

    &__add-statement {
      margin-top: $space-sm;
    }
  }

  .bearing-read {
    &__bar {
      flex: 1;
      height: 4px;
      background: $color-border;
      border-radius: 2px;
      overflow: hidden;
      max-width: 120px;
    }

    &__fill {
      height: 100%;
      background: $una-mid-green;
      border-radius: 2px;
      transition: width 600ms ease;
    }

    &__label {
      font-family: $font-mono;
      font-size: 0.65rem;
      color: $una-mid-green;
      white-space: nowrap;
    }
  }

  .statements-list {
    list-style: none;
    padding: 0;
    margin: $space-sm 0 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .statement {
    display: flex;
    gap: $space-xs;
    align-items: baseline;
    font-family: $font-sans;
    font-size: 0.8rem;
    color: $una-mid-green;

    &__indicator {
      font-family: $font-mono;
      font-size: 0.75rem;
      width: 12px;
      flex-shrink: 0;
    }

    &.observed { color: $una-dark-1; }
    &.not-observed { opacity: 0.6; }
  }

  .statement-input {
    width: 100%;
    font-family: $font-sans;
    font-size: 0.8rem;
    border: 1px solid transparent;
    border-bottom-color: $color-border;
    background: transparent;
    padding: $space-xs 0;
    color: $una-dark-1;

    &::placeholder { color: $una-mid-green; }
    &:focus {
      outline: none;
      border-color: $color-border;
      border-radius: 3px;
      padding: $space-xs $space-sm;
    }
  }

  .add-bearing {
    border-top: 1px solid $color-border;
    padding-top: $space-xl;
    display: flex;
    flex-direction: column;
    gap: $space-sm;

    &__heading {
      font-family: $font-sans;
      font-size: 0.78rem;
      font-weight: 600;
      color: $una-mid-green;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 0;
    }

    &__text {
      font-family: $font-sans;
      font-size: 0.9rem;
      border: 1px solid $color-border;
      border-radius: 3px;
      padding: $space-sm;
      resize: vertical;

      &:focus { outline: 1px solid $una-mid-green; }
    }

    &__weight-label {
      display: flex;
      flex-direction: column;
      gap: $space-xs;
      font-family: $font-mono;
      font-size: 0.68rem;
      color: $una-mid-green;
    }

    &__slider {
      width: 100%;
    }
  }

  .btn-primary {
    align-self: flex-start;
    font-family: $font-sans;
    font-size: 0.82rem;
    padding: $space-xs $space-md;
    background: $una-dark-1;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;

    &:disabled { opacity: 0.5; cursor: default; }
    &:not(:disabled):hover { background: $una-mid-green; }
  }

  .btn-save {
    font-family: $font-sans;
    font-size: 0.8rem;
    padding: $space-xs $space-sm;
    background: $una-dark-1;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    &:hover { background: $una-mid-green; }
  }

  .btn-cancel {
    font-family: $font-sans;
    font-size: 0.8rem;
    padding: $space-xs $space-sm;
    background: none;
    border: 1px solid $color-border;
    border-radius: 3px;
    cursor: pointer;
    color: $una-mid-green;
    &:hover { background: $una-light-green; }
  }

  .btn-text {
    font-family: $font-sans;
    font-size: 0.75rem;
    background: none;
    border: none;
    cursor: pointer;
    color: $una-mid-green;
    padding: 0;

    &:hover { color: $una-dark-1; text-decoration: underline; }

    &--danger:hover { color: #c0392b; text-decoration: underline; }
  }
</style>
