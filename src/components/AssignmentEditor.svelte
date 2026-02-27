<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import Placeholder from '@tiptap/extension-placeholder';

  export let content: string = '';
  export let placeholder: string = 'What will students do here?';
  export let onUpdate: (html: string) => void = () => {};

  let element: HTMLElement;
  let editor: Editor;

  onMount(() => {
    editor = new Editor({
      element,
      extensions: [
        StarterKit,
        Placeholder.configure({ placeholder }),
      ],
      content,
      editorProps: {
        attributes: {
          class: 'assignment-editor__body',
        },
      },
      onUpdate({ editor }) {
        onUpdate(editor.getHTML());
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
  </div>

  <div class="assignment-editor__surface" bind:this={element}></div>
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

  .assignment-editor__surface {
    flex: 1;
    padding: $space-lg;
    overflow-y: auto;

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
    }
  }
</style>
