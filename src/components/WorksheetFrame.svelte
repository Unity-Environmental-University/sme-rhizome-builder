<script lang="ts">
  import { onMount } from 'svelte';
  import { session } from '../stores/session';
  import type { Message } from '../stores/session';
  import { courseContext, loadCourses } from '../stores/courseContext';
  import { settings } from '../stores/settings';
  import OutcomeCoverage from './OutcomeCoverage.svelte';
  import { get } from 'svelte/store';
  import axios from 'axios';

  function exportSession() {
    const ctx = get(courseContext);
    const s = get(session);
    const data = {
      courseContext: ctx,
      messages: s.messages,
      assignments: s.assignments,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const slug = ctx.courseCode.replace(/\s+/g, '-').toLowerCase() || 'session';
    a.href = url;
    a.download = `${slug}-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  let inputValue = '';

  onMount(() => {
    loadCourses().catch(err => {
      console.error('[WorksheetFrame] loadCourses failed on mount:', err);
    });
  });

  function computeOpener(ctx: typeof $courseContext): string {
    const outcomes = ctx.learningOutcomes?.trim();
    if (outcomes) {
      const lines = outcomes.split('\n')
        .map(l => l.replace(/^[-*\d.)]+\s*/, '').trim())
        .filter(Boolean);
      if (lines.length > 0) {
        return `Tell me about a moment in your field when this mattered:\n\n"${lines[0]}"`;
      }
    }
    const discipline = ctx.courseTitle || ctx.courseCode;
    if (discipline) {
      return `What's something about ${discipline} that's hard to describe to someone not in it?`;
    }
    return "What's something about your discipline that's hard to describe to someone not in it?";
  }

  $: opener = computeOpener($courseContext);

  async function submit() {
    const content = inputValue.trim();
    if (!content || $session.loading) return;

    inputValue = '';

    const isFirst = $session.messages.length === 0;
    const toAdd: Message[] = isFirst
      ? [{ role: 'assistant', content: opener }, { role: 'user', content }]
      : [{ role: 'user', content }];

    session.update(s => ({
      ...s,
      messages: [...s.messages, ...toAdd],
      loading: true,
      error: null,
    }));

    try {
      const res = await axios.post(
        '/api/chat',
        {
          messages: [...$session.messages],
          session_id: $session.dbSessionId,
          api_key: $settings.apiKey || undefined,
          endpoint: $settings.aiEndpoint,
          base_url: $settings.aiBaseUrl || undefined,
          model: $settings.aiModel || undefined,
        },
        { withCredentials: true }
      );

      const { reply, assignment } = res.data;

      session.update(s => {
        const newAssignments = assignment
          ? [...s.assignments, { module: '', ...assignment }]
          : s.assignments;
        return {
          ...s,
          messages: [...s.messages, { role: 'assistant', content: reply }],
          assignments: newAssignments,
          drawerIndex: newAssignments.length > 0 ? newAssignments.length - 1 : 0,
          drawerOpen: assignment != null ? true : s.drawerOpen,
          loading: false,
        };
      });
    } catch (err: unknown) {
      const message = axios.isAxiosError(err)
        ? (err.response?.data?.error ?? err.message)
        : err instanceof Error ? err.message : 'Request failed';
      console.error('[chat] submit failed:', err);
      session.update(s => ({ ...s, loading: false, error: message }));
    }
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit();
  }

  function openDrawer() {
    session.update(s => ({ ...s, drawerOpen: true }));
  }
</script>

<main class="worksheet">
  <header class="worksheet__header">
    <div class="worksheet__heading">
      <h1 class="worksheet__title">SME Rhizome Builder</h1>
      <p class="worksheet__subtitle">
        {#if $courseContext.courseCode}
          {$courseContext.courseCode}{$courseContext.courseTitle ? ` — ${$courseContext.courseTitle}` : ''}
        {:else}
          Explore your discipline. Shape an assignment that belongs to it.
        {/if}
      </p>
    </div>
    {#if $session.messages.length > 0}
      <button class="worksheet__export" type="button" on:click={exportSession} title="Export session as JSON">
        export ↓
      </button>
    {/if}
  </header>

  <section class="worksheet__conversation" aria-label="Conversation" aria-live="polite">
    {#if $session.messages.length === 0}
      <article class="message message--assistant">
        <p class="message__speaker" aria-hidden="true">Rhizome</p>
        <p class="message__content">{opener}</p>
      </article>
    {:else}
      {#each $session.messages as msg (msg)}
        <article class="message message--{msg.role}" aria-label="{msg.role === 'user' ? 'You' : 'Rhizome'}">
          <p class="message__speaker" aria-hidden="true">{msg.role === 'user' ? 'You' : 'Rhizome'}</p>
          <p class="message__content">{msg.content}</p>
        </article>
      {/each}
    {/if}

    {#if $session.loading}
      <p class="message message--assistant message--thinking" role="status">thinking…</p>
    {/if}
  </section>

  <OutcomeCoverage />

  {#if $session.error}
    <p role="alert" class="worksheet__error">{$session.error}</p>
  {/if}

  <section class="worksheet__reply">
    <form on:submit|preventDefault={submit}>
      <label class="worksheet__reply-label" for="response">Your response</label>
      <textarea
        id="response"
        class="worksheet__textarea"
        bind:value={inputValue}
        on:keydown={handleKey}
        disabled={$session.loading}
        rows={5}
        placeholder="Write freely. The tool will help you find the shape."
      ></textarea>
      <div class="worksheet__actions">
        <button
          class="worksheet__submit"
          type="submit"
          disabled={$session.loading || !inputValue.trim()}
        >
          {$session.loading ? 'thinking…' : 'submit'}
        </button>
        {#if $session.assignments.length > 0}
          <button class="worksheet__open-drawer" type="button" on:click={openDrawer}>
            {$session.assignments.length === 1 ? 'view assignment →' : `view assignments (${$session.assignments.length}) →`}
          </button>
        {/if}
      </div>
      <p class="worksheet__hint">⌘↵ or Ctrl↵ to submit</p>
    </form>
  </section>
</main>

<style lang="scss">
  .worksheet {
    max-width: 720px;
    margin: $space-xl auto;
    padding: $space-lg;
    background: $color-bg-paper;
    border-top: $border-top;
    box-shadow: $shadow-paper;
  }

  .worksheet__header {
    margin-bottom: $space-lg;
    border-bottom: 1px solid $color-border;
    padding-bottom: $space-md;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: $space-md;
  }

  .worksheet__heading {
    flex: 1;
  }

  .worksheet__export {
    background: none;
    border: 1px solid $color-border;
    color: $una-mid-green;
    padding: $space-xs $space-sm;
    font-family: $font-sans;
    font-size: 0.8rem;
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;

    &:hover {
      border-color: $una-gold;
      color: $una-dark-1;
    }
  }

  .worksheet__title {
    font-family: $font-serif;
    font-size: 1.6rem;
    font-weight: normal;
    margin: 0 0 $space-xs;
    color: $una-dark-1;
  }

  .worksheet__subtitle {
    font-family: $font-serif;
    font-size: 0.95rem;
    color: $una-mid-green;
    margin: 0;
    font-style: italic;
  }

  .worksheet__conversation {
    margin-bottom: $space-lg;
    display: flex;
    flex-direction: column;
    gap: $space-md;
  }

  .message {
    &__speaker {
      display: block;
      font-family: $font-sans;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: $una-mid-green;
      margin: 0 0 $space-xs;
    }

    &__content {
      margin: 0;
      font-family: $font-serif;
      line-height: 1.65;
      white-space: pre-wrap;
    }

    &--user {
      padding: $space-md;
      background: $una-light-green;
      border-left: 3px solid $una-gold;
    }

    &--assistant {
      padding: $space-md 0;
    }

    &--thinking .message__content {
      color: $una-mid-green;
      font-style: italic;
    }
  }

  .worksheet__error {
    padding: $space-sm $space-md;
    background: #fde;
    border: 1px solid #e88;
    margin-bottom: $space-md;
    font-size: 0.9rem;
  }

  .worksheet__reply {
    background: $una-light-green;
    padding: $space-md;
    margin-top: $space-md;
  }

  .worksheet__reply-label {
    display: block;
    font-family: $font-sans;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: $una-mid-green;
    margin-bottom: $space-sm;
  }

  .worksheet__textarea {
    width: 100%;
    font-family: $font-serif;
    font-size: 1rem;
    line-height: 1.65;
    padding: $space-sm;
    border: 1px solid $color-border;
    background: white;
    color: $color-text;
    resize: vertical;

    &:focus {
      outline: 2px solid $una-gold;
      outline-offset: 1px;
    }

    &:disabled {
      opacity: 0.6;
    }
  }

  .worksheet__actions {
    display: flex;
    gap: $space-sm;
    margin-top: $space-sm;
    align-items: center;
  }

  .worksheet__submit {
    background: $una-dark-1;
    color: white;
    border: none;
    padding: $space-sm $space-lg;
    font-family: $font-sans;
    font-size: 0.9rem;
    cursor: pointer;
    letter-spacing: 0.05em;

    &:hover:not(:disabled) {
      background: $una-dark-2;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  .worksheet__open-drawer {
    background: none;
    border: 1px solid $una-gold;
    color: $una-dark-1;
    padding: $space-sm $space-md;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;

    &:hover {
      background: $una-gold;
    }
  }

  .worksheet__hint {
    font-size: 0.75rem;
    color: $una-mid-green;
    margin: $space-xs 0 0;
  }
</style>
