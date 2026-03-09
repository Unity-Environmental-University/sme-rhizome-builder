import { Mark, mergeAttributes } from '@tiptap/core';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    comment: {
      setComment: (commentId: string, from: number, to: number, source?: 'agent' | 'sme' | 'ld') => ReturnType;
      removeComment: (commentId: string) => ReturnType;
    };
  }
}

export const CommentMark = Mark.create({
  name: 'comment',

  // Overlapping marks allowed. Two questions in the same passage is real.
  // Don't clear the range on insert. Discourage in practice, not in code.

  addAttributes() {
    return {
      commentId: {
        default: null,
        parseHTML: el => el.getAttribute('data-comment-id'),
        renderHTML: attrs => ({ 'data-comment-id': attrs.commentId }),
      },
      // 'agent' | 'sme' | 'ld' — drives shader color via EditorCanvas SOURCE_COLORS
      source: {
        default: 'agent',
        parseHTML: el => el.getAttribute('data-source'),
        renderHTML: attrs => ({ 'data-source': attrs.source }),
      },
      // Drives 2.5× intensity in the shader. Set reactively, not persisted in HTML.
      unread: {
        default: false,
        renderHTML: attrs => attrs.unread ? { 'data-unread': '' } : {},
      },
    };
  },

  parseHTML() {
    return [{ tag: 'mark[data-comment-id]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['mark', mergeAttributes(HTMLAttributes, { class: 'comment-anchor' }), 0];
  },

  addCommands() {
    return {
      setComment:
        (commentId: string, from: number, to: number, source: 'agent' | 'sme' | 'ld' = 'agent') =>
        ({ chain }) => {
          return chain()
            .setTextSelection({ from, to })
            .setMark('comment', { commentId, source })
            .run();
        },

      removeComment:
        (commentId: string) =>
        ({ tr, state, dispatch }) => {
          state.doc.descendants((node, pos) => {
            node.marks.forEach(mark => {
              if (mark.type.name === 'comment' && mark.attrs.commentId === commentId) {
                tr.removeMark(pos, pos + node.nodeSize, mark.type);
              }
            });
          });
          if (dispatch) dispatch(tr);
          return true;
        },
    };
  },

});
