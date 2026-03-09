<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import Placeholder from '@tiptap/extension-placeholder';
  import axios from 'axios';
  import EditorCanvas from './EditorCanvas.svelte';
  import type { MarkData } from './EditorCanvas.svelte';
  import { CommentMark } from './CommentMark';
  import { openThread, notifyLogChanged } from '../stores/threads';

  export let content: string = '';
  export let placeholder: string = 'What will students do here?';
  export let onUpdate: (html: string) => void = () => {};
  export let assignmentId: string | null = null;

  let surface: HTMLElement;
  let element: HTMLElement;
  let editor: Editor;
  let canvasMarks: MarkData[] = [];
  let hasSelection = false;

  // Expose: place a comment mark on the current selection, returns the commentId
  export function getSelection(): { from: number; to: number; text: string } | null {
    if (!editor) return null;
    const { from, to } = editor.state.selection;
    if (from === to) return null;
    return { from, to, text: editor.state.doc.textBetween(from, to) };
  }

  export function placeComment(commentId: string, from: number, to: number, source: 'agent' | 'sme' | 'ld' = 'agent') {
    if (!editor) return;
    editor.commands.setComment(commentId, from, to, source);
  }

  async function handleUnstuck() {
    if (!assignmentId) return;
    const sel = getSelection();
    const commentId = crypto.randomUUID();
    const payload: Record<string, unknown> = {
      action_type: 'sme_anchor',
      content: JSON.stringify({
        comment_id: commentId,
        text: sel ? `[unstuck: "${sel.text}"]` : '[unstuck: whole draft]',
        source: 'sme',
        mode: 'unstuck',
        ...(sel ? { from: sel.from, to: sel.to } : {}),
      }),
    };

    try {
      const anchorRes = await axios.post(`/api/log/${assignmentId}`, payload, { withCredentials: true });
      if (sel) {
        placeComment(commentId, sel.from, sel.to, 'sme');
      }
      openThread(commentId);

      // Ask the concierge to respond — fire and don't block the UI
      axios.post(`/api/concierge/${assignmentId}`, {
        anchor_id: anchorRes.data.id,
        comment_id: commentId,
      }, { withCredentials: true }).then(() => {
        notifyLogChanged();
      }).catch(e => {
        console.error('[AssignmentEditor] concierge failed:', e);
      });
    } catch (e) {
      console.error('[AssignmentEditor] unstuck failed:', e);
    }
  }

  // Recompute canvas mark rects from DOM. Called lazily — only when the mark
  // set changes, not on every keystroke. Multi-line spans produce multiple rects
  // (one per line) so each line segment is its own heat source.
  function computeMarkRects() {
    if (!surface || !element) return;
    const surfaceRect = surface.getBoundingClientRect();
    const markEls = element.querySelectorAll('mark[data-comment-id]');
    const result: MarkData[] = [];

    markEls.forEach(el => {
      const commentId = el.getAttribute('data-comment-id')!;
      const source = (el.getAttribute('data-source') ?? 'agent') as 'agent' | 'sme' | 'ld';
      const unread = el.hasAttribute('data-unread');

      // getClientRects() gives one rect per line for wrapped inline elements
      Array.from(el.getClientRects()).forEach(r => {
        result.push({
          commentId,
          source,
          unread,
          rect: {
            left:   r.left   - surfaceRect.left,
            top:    r.top    - surfaceRect.top,
            right:  r.right  - surfaceRect.left,
            bottom: r.bottom - surfaceRect.top,
          },
        });
      });
    });

    canvasMarks = result;
  }

  onMount(() => {
    editor = new Editor({
      element,
      extensions: [
        StarterKit,
        Placeholder.configure({ placeholder }),
        CommentMark,
      ],
      content,
      editorProps: {
        attributes: {
          class: 'assignment-editor__body',
        },
        handleClick(view, _pos, event) {
          const target = event.target as HTMLElement;
          const markEl = target.closest('mark[data-comment-id]');
          if (markEl) {
            const commentId = markEl.getAttribute('data-comment-id');
            if (commentId) openThread(commentId);
            return true; // consumed
          }
          return false;
        },
      },
      onCreate() {
        Promise.resolve().then(computeMarkRects);
      },
      onSelectionUpdate({ editor: e }) {
        const { from, to } = e.state.selection;
        hasSelection = from !== to;
      },
      onUpdate({ editor: e }) {
        onUpdate(e.getHTML());
        // Recompute on every doc change — marks may have moved with the text
        Promise.resolve().then(computeMarkRects);
      },
    });
  });

  onDestroy(() => {
    editor?.destroy();
  });
</script>

<div class="assignment-editor">
  <div class="assignment-editor__toolbar">
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('bold')}
      on:click={() => editor.chain().focus().toggleBold().run()}
      title="Bold"
    >B</button>
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('italic')}
      on:click={() => editor.chain().focus().toggleItalic().run()}
      title="Italic"
    ><em>i</em></button>
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('bulletList')}
      on:click={() => editor.chain().focus().toggleBulletList().run()}
      title="Bullet list"
    >—</button>
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('orderedList')}
      on:click={() => editor.chain().focus().toggleOrderedList().run()}
      title="Numbered list"
    >1.</button>
    <span class="assignment-editor__divider"></span>
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('heading', { level: 2 })}
      on:click={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      title="Heading"
    >H</button>
    <button
      class="assignment-editor__tool"
      class:active={editor?.isActive('blockquote')}
      on:click={() => editor.chain().focus().toggleBlockquote().run()}
      title="Blockquote"
    >"</button>
    <span class="assignment-editor__divider"></span>
    <button
      class="assignment-editor__tool assignment-editor__unstuck"
      class:active={hasSelection}
      on:click={handleUnstuck}
      title={hasSelection ? 'Ask about this passage' : 'Ask for help with the whole draft'}
      disabled={!assignmentId}
    >?</button>
  </div>

  <div class="assignment-editor__surface" bind:this={surface}>
    <EditorCanvas marks={canvasMarks} />
    <div class="assignment-editor__body-host" bind:this={element}></div>
  </div>
</div>

<style lang="scss">
  .assignment-editor {
    display: flex;
    flex-direction: column;
    border: 1px solid $color-border;
    background: white;
    min-height: 320px;
  }

  .assignment-editor__toolbar {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: $space-xs $space-sm;
    border-bottom: 1px solid $color-border;
    background: $una-light-green;
    flex-shrink: 0;
  }

  .assignment-editor__tool {
    background: none;
    border: 1px solid transparent;
    padding: 2px $space-xs;
    font-family: $font-sans;
    font-size: 0.85rem;
    cursor: pointer;
    color: $una-mid-green;
    min-width: 24px;
    text-align: center;

    &:hover {
      background: white;
      border-color: $color-border;
      color: $una-dark-1;
    }

    &.active {
      background: white;
      border-color: $una-gold;
      color: $una-dark-1;
    }
  }

  .assignment-editor__divider {
    width: 1px;
    height: 16px;
    background: $color-border;
    margin: 0 $space-xs;
  }

  .assignment-editor__unstuck {
    font-family: $font-serif;
    font-style: italic;
    font-weight: 600;
    color: $una-gold;

    &.active {
      border-color: $una-gold;
      background: rgba(196, 164, 75, 0.08);
    }
  }

  .assignment-editor__surface {
    flex: 1;
    position: relative;
    overflow-y: auto;
  }

  .assignment-editor__body-host {
    position: relative;
    z-index: 1;
    padding: $space-lg;

    :global(.assignment-editor__body) {
      outline: none;
      font-family: $font-serif;
      font-size: 1rem;
      line-height: 1.7;
      color: $color-text;
      min-height: 240px;

      :global(h2) {
        font-family: $font-serif;
        font-size: 1.1rem;
        font-weight: 600;
        margin: $space-lg 0 $space-sm;
        color: $una-dark-1;
      }

      :global(p) {
        margin: 0 0 $space-sm;
      }

      :global(ul), :global(ol) {
        padding-left: $space-lg;
        margin: 0 0 $space-sm;
      }

      :global(blockquote) {
        border-left: 3px solid $una-gold;
        margin: 0 0 $space-sm;
        padding-left: $space-md;
        color: $una-mid-green;
        font-style: italic;
      }

      :global(p.is-editor-empty:first-child::before) {
        content: attr(data-placeholder);
        float: left;
        color: $una-mid-green;
        opacity: 0.6;
        pointer-events: none;
        height: 0;
        font-style: italic;
      }

      :global(mark.comment-anchor) {
        background: transparent;
        border-bottom: 1.5px solid rgba(196, 164, 75, 0.45);
        cursor: pointer;
        transition: border-color 200ms ease, background 200ms ease;

        &:hover {
          background: rgba(196, 164, 75, 0.08);
          border-color: rgba(196, 164, 75, 0.7);
        }
      }

      :global(mark.comment-anchor[data-source="sme"]) {
        border-color: rgba(120, 140, 100, 0.4);
        &:hover { background: rgba(120, 140, 100, 0.06); border-color: rgba(120, 140, 100, 0.65); }
      }

      :global(mark.comment-anchor[data-source="ld"]) {
        border-color: rgba(100, 140, 180, 0.4);
        &:hover { background: rgba(100, 140, 180, 0.06); border-color: rgba(100, 140, 180, 0.65); }
      }

      :global(mark.comment-anchor[data-unread]) {
        border-bottom-width: 2px;
      }

    }
  }

</style>
