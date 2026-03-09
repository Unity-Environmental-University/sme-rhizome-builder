/**
 * CommentMark — sketch / thinking-out-loud
 *
 * A TipTap Mark that carries a `commentId` — a UUID that connects a highlighted
 * span in the document to a thread of log_entries on the server.
 * Click the highlight → sidebar opens to that thread.
 */

import { Mark, mergeAttributes } from '@tiptap/core'

// ── The mark itself ───────────────────────────────────────────────────────────

export const CommentMark = Mark.create({
  name: 'comment',

  // Overlapping marks are allowed. Two questions living in the same passage is
  // real. Don't clear the range when a new mark is placed. Discourage it in
  // practice (the agent shouldn't pile on) but don't enforce it in code.
  // Additive color blending considered — too fancy for now. Revisit if it
  // gets visually noisy in use.

  addAttributes() {
    return {
      commentId: {
        default: null,
        parseHTML: el => el.getAttribute('data-comment-id'),
        renderHTML: attrs => ({ 'data-comment-id': attrs.commentId }),
      },

      // Three sources, three visual treatments. Already reflected in
      // EditorCanvas SOURCE_COLORS: agent = warm gold, sme = warm white, ld = cool blue.
      // The sidebar content also tells you who initiated — the visual distinction
      // is ambient, not load-bearing for comprehension.
      source: {
        default: 'agent',
        parseHTML: el => el.getAttribute('data-source'),
        renderHTML: attrs => ({ 'data-source': attrs.source }),
      },

      // Unread drives the shader — unread marks glow at 2.5× base intensity.
      // Set reactively from the sidebar, not persisted in HTML.
      unread: {
        default: false,
        renderHTML: attrs => attrs.unread ? { 'data-unread': '' } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'mark[data-comment-id]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['mark', mergeAttributes(HTMLAttributes, { class: 'comment-anchor' }), 0]
  },

  addCommands() {
    return {
      // Flow: server receives full document content + positions from the frontend.
      // Server creates log_entry, returns commentId + the confirmed {from, to}.
      // Frontend applies mark: editor.chain().setTextSelection({from, to}).setComment(commentId).
      //
      // The server needs document content constantly — positions come from the
      // frontend, not discovered server-side. Race conditions handled via the
      // ProseMirror transaction stack: positions are remapped through each
      // transaction as edits happen. This is also the undo story, so the
      // mutation tracking is load-bearing for two things at once.
      setComment:
        (commentId: string, from: number, to: number) =>
        ({ commands }) => {
          return commands.setMark('comment', { commentId })
          // For agent-initiated highlights, caller sets selection first:
          // editor.chain().setTextSelection({ from, to }).setComment(commentId, from, to).run()
        },

      // Walk the document, remove marks matching this commentId.
      // SMEs can archive a thread (sidebar action, not mark removal).
      // LDs can delete (mark removed + log entries gone). Light permissions
      // layer handles the distinction — not enforced here in the mark itself.
      removeComment:
        (commentId: string) =>
        ({ tr, state }) => {
          state.doc.descendants((node, pos) => {
            node.marks.forEach(mark => {
              if (mark.type.name === 'comment' && mark.attrs.commentId === commentId) {
                tr.removeMark(pos, pos + node.nodeSize, mark.type)
              }
            })
          })
          return true
        },
    }
  },
})


// ── Mark survival across edits ────────────────────────────────────────────────

// When the SME edits highlighted text, positions are tracked through the
// ProseMirror transaction mapping stack — tr.mapping.map(pos) remaps {from, to}
// through each transaction as it's applied. If the highlighted text is deleted
// entirely, the positions collapse and the mark detaches. Detached threads
// appear in a sidebar section ("elsewhere in this draft" or similar).
//
// This is the same mechanism needed for undo anyway, so tracking the mutation
// stack serves both purposes.


// ── What the sidebar needs ────────────────────────────────────────────────────

// When the SME clicks a highlighted span:
//
//   onClick(view, pos) {
//     const marks = view.state.doc.resolve(pos).marks()
//     const comment = marks.find(m => m.type.name === 'comment')
//     if (comment) {
//       sidebar.openThread(comment.attrs.commentId)
//     }
//   }
//
// Clicking a highlight always opens the sidebar. The click is intentional.
// Sidebar starts open — a new SME won't know to look for it. Once open,
// they close it when they want to. The sidebar state is a Svelte writable
// shared by the editor and the sidebar component.


// ── The unstuck button and selection ─────────────────────────────────────────

// With selection:
//   const { from, to } = editor.state.selection
//   const spanText = editor.state.doc.textBetween(from, to)
//   // Send to server: { assignment_id, span_text, from, to, mode: 'unstuck' }
//   // Server creates log_entry, returns commentId
//   // Frontend: editor.chain().setTextSelection({from, to}).setComment(commentId, from, to).run()
//
// Without selection — hold off. There's a version where the agent proposes a
// changeset. For now: anchor in the text but not a span. The note appears in
// the sidebar; the document gets some kind of anchor marker, shape TBD.
// Not a pure chat reply — it needs a home in the document, even if imprecise.
