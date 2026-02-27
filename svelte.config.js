import preprocess from 'svelte-preprocess';

export default {
  preprocess: preprocess({
    typescript: {},
    scss: {
      prependData: `@use 'src/styles/theme' as *;`
    }
  })
};
