<script lang="ts">
  import { courseContext, courseList, saveCourse, selectCourse, newCourse } from '../stores/courseContext';
  import { resetSession } from '../stores/session';
  import { user, logout } from '../stores/auth';
  import { settings } from '../stores/settings';
  import { api } from '../lib/api';

  type CanvasAssignment = { id: number; name: string; points_possible: number; html_url: string; has_rubric: boolean };
  let canvasAssignments: CanvasAssignment[] = [];
  let canvasLoading = false;
  let canvasError = '';

  async function fetchCanvasAssignments() {
    if (!$courseContext.canvasCourseId) return;
    canvasLoading = true;
    canvasError = '';
    canvasAssignments = [];
    try {
      const res = await api.get('/api/canvas/assignments', {
        params: { canvas_course_id: $courseContext.canvasCourseId },
      });
      canvasAssignments = res.data.assignments;
    } catch (err: unknown) {
      canvasError = err instanceof Error ? err.message : 'Failed to fetch';
    } finally {
      canvasLoading = false;
    }
  }

  function handleCourseSelect(e: Event) {
    const id = parseInt((e.target as HTMLSelectElement).value);
    if (id === -1) { newCourse(); return; }
    const item = $courseList.find(c => c.id === id);
    if (item) { selectCourse(item); resetSession(); }
  }

  export let open = false;

  function close() { open = false; }

  let saved = false;
  let saveError = '';
  async function save() {
    saveError = '';
    try {
      await saveCourse();
      saved = true;
      setTimeout(() => { saved = false; }, 1800);
    } catch {
      saveError = 'Save failed — check your connection and try again.';
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // logout() already logs — just close the drawer
    }
    open = false;
  }

  function clearAll() {
    resetSession();
    open = false;
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="backdrop" on:click={close} role="presentation"></div>

  <aside class="settings" aria-label="Settings">
    <div class="settings__header">
      <h2 class="settings__title">Settings</h2>
      <button class="settings__close" on:click={close} aria-label="Close settings">✕</button>
    </div>

    <div class="settings__body">

      {#if $user}
        <section class="settings__group settings__user">
          <p class="settings__user-name">{$user.name}</p>
          <p class="settings__user-email">{$user.email}</p>
          <button class="settings__logout" on:click={handleLogout}>sign out</button>
        </section>
      {/if}

      <section class="settings__group">
        <h3 class="settings__group-title">Course</h3>

        {#if $courseList.length > 0}
          <label class="settings__label" for="course-select">Your courses</label>
          <select
            id="course-select"
            class="settings__input"
            on:change={handleCourseSelect}
            value={$courseContext.id ?? ''}
          >
            {#each $courseList as c}
              <option value={c.id}>{c.courseCode}{c.courseTitle ? ` — ${c.courseTitle}` : ''}</option>
            {/each}
            <option value={-1}>+ New course</option>
          </select>
        {/if}

        <label class="settings__label" for="course-code">Course code</label>
        <input
          id="course-code"
          class="settings__input"
          type="text"
          placeholder="MARI 515"
          bind:value={$courseContext.courseCode}
          autocomplete="off"
          spellcheck={false}
        />

        <label class="settings__label" for="course-title">Course title</label>
        <input
          id="course-title"
          class="settings__input"
          type="text"
          placeholder="Coral Ecology and Conservation"
          bind:value={$courseContext.courseTitle}
          autocomplete="off"
        />

        <label class="settings__label" for="course-canvas-id">
          Canvas course ID
          <span class="settings__label-hint">(optional)</span>
        </label>
        <input
          id="course-canvas-id"
          class="settings__input"
          type="text"
          placeholder="123456"
          bind:value={$courseContext.canvasCourseId}
          autocomplete="off"
          spellcheck={false}
        />

        <label class="settings__label" for="course-outcomes">
          Learning outcomes
          <span class="settings__label-hint">(paste from syllabus, one per line)</span>
        </label>
        <textarea
          id="course-outcomes"
          class="settings__input settings__textarea"
          placeholder="Students will be able to…"
          bind:value={$courseContext.learningOutcomes}
          rows={6}
          spellcheck={false}
        ></textarea>
      </section>

      <section class="settings__group">
        <h3 class="settings__group-title">AI</h3>

        <label class="settings__label" for="ai-endpoint">Endpoint</label>
        <select id="ai-endpoint" class="settings__input" bind:value={$settings.aiEndpoint}>
          <option value="anthropic">Anthropic (Claude)</option>
          <option value="openai">OpenAI-compatible</option>
          <option value="ollama">Ollama (local)</option>
        </select>

        {#if $settings.aiEndpoint !== 'ollama'}
          <label class="settings__label" for="ai-key">
            API key
            <span class="settings__label-hint">(stored in browser only)</span>
          </label>
          <input
            id="ai-key"
            class="settings__input"
            type="password"
            placeholder={$settings.aiEndpoint === 'openai' ? 'sk-…' : 'sk-ant-…'}
            bind:value={$settings.apiKey}
            autocomplete="off"
            spellcheck={false}
          />
        {/if}

        {#if $settings.aiEndpoint === 'openai' || $settings.aiEndpoint === 'ollama'}
          <label class="settings__label" for="ai-base-url">
            Base URL
            <span class="settings__label-hint">
              {$settings.aiEndpoint === 'ollama' ? '(default: localhost:11434)' : '(default: api.openai.com/v1)'}
            </span>
          </label>
          <input
            id="ai-base-url"
            class="settings__input"
            type="text"
            placeholder={$settings.aiEndpoint === 'ollama' ? 'http://localhost:11434/v1' : 'https://api.openai.com/v1'}
            bind:value={$settings.aiBaseUrl}
            autocomplete="off"
            spellcheck={false}
          />
        {/if}

        <label class="settings__label" for="ai-model">
          Model
          <span class="settings__label-hint">(optional override)</span>
        </label>
        <input
          id="ai-model"
          class="settings__input"
          type="text"
          list="ai-model-list"
          placeholder={
            $settings.aiEndpoint === 'ollama' ? 'qwen2.5:7b' :
            $settings.aiEndpoint === 'openai' ? 'gpt-4o-mini' :
            'claude-haiku-4-5-20251001'
          }
          bind:value={$settings.aiModel}
          autocomplete="off"
          spellcheck={false}
        />
        <datalist id="ai-model-list">
          {#if $settings.aiEndpoint === 'anthropic'}
            <option value="claude-haiku-4-5-20251001" />
            <option value="claude-sonnet-4-6" />
            <option value="claude-opus-4-6" />
          {:else if $settings.aiEndpoint === 'openai'}
            <option value="gpt-4o-mini" />
            <option value="gpt-4o" />
            <option value="o1-mini" />
            <option value="o3-mini" />
          {:else if $settings.aiEndpoint === 'ollama'}
            <option value="qwen2.5:7b" />
            <option value="qwen2.5:14b" />
            <option value="qwen2.5:32b" />
            <option value="llama3.2:3b" />
            <option value="llama3.2" />
            <option value="mistral" />
            <option value="phi4" />
          {/if}
        </datalist>
      </section>

      {#if $courseContext.canvasCourseId}
        <section class="settings__group">
          <h3 class="settings__group-title">Existing Canvas Assignments</h3>
          <button class="settings__fetch-btn" on:click={fetchCanvasAssignments} disabled={canvasLoading}>
            {canvasLoading ? 'loading…' : 'fetch from Canvas'}
          </button>
          {#if canvasError}
            <p class="settings__canvas-error">{canvasError}</p>
          {/if}
          {#if canvasAssignments.length > 0}
            <ul class="settings__canvas-list">
              {#each canvasAssignments as a}
                <li>
                  <a href={a.html_url} target="_blank" rel="noreferrer" class="settings__canvas-link">
                    {a.name}
                  </a>
                  <span class="settings__canvas-meta">
                    {a.points_possible}pts{a.has_rubric ? ' · rubric' : ''}
                  </span>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/if}
    </div>

    {#if saveError}
      <p class="settings__save-error">{saveError}</p>
    {/if}

    <div class="settings__footer">
      <button class="settings__save" on:click={save}>
        {saved ? '✓ saved' : 'save'}
      </button>
      <button class="settings__clear" on:click={clearAll}>
        clear session
      </button>
    </div>
  </aside>
{/if}

<style lang="scss">
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba($una-dark-1, 0.3);
    z-index: 10;
  }

  .settings {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: 360px;
    max-width: 100vw;
    background: $color-bg-paper;
    border-right: 1px solid $color-border;
    border-top: $border-top;
    z-index: 11;
    display: flex;
    flex-direction: column;
    box-shadow: 4px 0 16px rgba($una-dark-1, 0.15);
  }

  .settings__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $space-md $space-lg;
    border-bottom: 1px solid $color-border;
    flex-shrink: 0;
  }

  .settings__title {
    font-family: $font-serif;
    font-size: 1.1rem;
    font-weight: normal;
    margin: 0;
  }

  .settings__close {
    background: none;
    border: none;
    font-size: 1.1rem;
    cursor: pointer;
    color: $una-mid-green;
    padding: $space-xs;
    &:hover { color: $una-dark-1; }
  }

  .settings__body {
    flex: 1;
    overflow-y: auto;
    padding: $space-md $space-lg;
    display: flex;
    flex-direction: column;
    gap: $space-lg;
  }

  .settings__user {
    padding: $space-sm $space-md;
    background: $una-light-green;
    border-left: 3px solid $una-gold;
    gap: 2px !important;
  }

  .settings__user-name {
    font-family: $font-serif;
    font-size: 0.95rem;
    color: $una-dark-1;
    margin: 0;
    font-weight: 600;
  }

  .settings__user-email {
    font-family: $font-sans;
    font-size: 0.8rem;
    color: $una-mid-green;
    margin: 0 0 $space-xs;
  }

  .settings__logout {
    background: none;
    border: 1px solid $color-border;
    color: $una-mid-green;
    font-family: $font-sans;
    font-size: 0.78rem;
    padding: 2px $space-sm;
    cursor: pointer;
    align-self: flex-start;
    &:hover { color: $una-dark-1; border-color: $una-mid-green; }
  }

  .settings__group {
    display: flex;
    flex-direction: column;
    gap: $space-sm;
  }

  .settings__group-title {
    font-family: $font-sans;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: $una-mid-green;
    margin: 0;
  }

  .settings__label {
    font-family: $font-sans;
    font-size: 0.85rem;
    color: $una-dark-1;
    margin-bottom: -$space-xs;
  }

  .settings__input {
    font-family: $font-mono;
    font-size: 0.85rem;
    padding: $space-xs $space-sm;
    border: 1px solid $color-border;
    background: white;
    color: $color-text;
    width: 100%;

    &:focus {
      outline: 2px solid $una-gold;
      outline-offset: 1px;
    }
  }

  .settings__textarea {
    resize: vertical;
    line-height: 1.5;
  }

  .settings__label-hint {
    font-weight: normal;
    font-size: 0.75rem;
    color: $una-mid-green;
    margin-left: $space-xs;
  }

  .settings__fetch-btn {
    background: $una-light-green;
    border: 1px solid $color-border;
    color: $una-dark-1;
    padding: $space-xs $space-md;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;
    &:hover:not(:disabled) { border-color: $una-gold; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  .settings__canvas-error {
    font-size: 0.8rem;
    color: #c00;
    margin: $space-xs 0 0;
  }

  .settings__canvas-list {
    list-style: none;
    margin: $space-sm 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .settings__canvas-list li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: $space-sm;
    padding: $space-xs 0;
    border-bottom: 1px solid $color-border;
    &:last-child { border-bottom: none; }
  }

  .settings__canvas-link {
    font-family: $font-serif;
    font-size: 0.85rem;
    color: $una-dark-1;
    text-decoration: none;
    &:hover { text-decoration: underline; color: $una-mid-green; }
  }

  .settings__canvas-meta {
    font-family: $font-sans;
    font-size: 0.72rem;
    color: $una-mid-green;
    white-space: nowrap;
  }

  .settings__footer {
    flex-shrink: 0;
    padding: $space-md $space-lg;
    border-top: 1px solid $color-border;
    display: flex;
    gap: $space-sm;
  }

  .settings__save-error {
    font-family: $font-sans;
    font-size: 0.78rem;
    color: #c00;
    margin: 0 $space-lg $space-xs;
  }

  .settings__save {
    flex: 1;
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-sm;
    font-family: $font-sans;
    font-size: 0.9rem;
    cursor: pointer;

    &:hover { background: $una-dark-2; }
  }

  .settings__clear {
    background: none;
    border: 1px solid $color-border;
    color: $una-mid-green;
    padding: $space-sm $space-md;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;

    &:hover {
      border-color: $una-mid-green;
      color: $una-dark-1;
    }
  }
</style>
