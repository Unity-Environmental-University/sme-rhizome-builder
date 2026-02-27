<script lang="ts">
  import { onMount } from 'svelte';
  import CourseMap from './components/CourseMap.svelte';
  import SettingsDrawer from './components/SettingsDrawer.svelte';
  import LoginScreen from './components/LoginScreen.svelte';
  import { user, authLoading, loadUser } from './stores/auth';

  let settingsOpen = false;

  onMount(() => {
    loadUser();
  });
</script>

{#if $authLoading}
  <!-- silent — brief flicker before auth resolves -->
{:else if $user === null}
  <LoginScreen />
{:else}
  <button class="settings-btn" on:click={() => settingsOpen = true} aria-label="Settings">
    ⚙
  </button>

  <CourseMap />
  <SettingsDrawer bind:open={settingsOpen} />
{/if}

<style lang="scss">
  .settings-btn {
    position: fixed;
    top: $space-md;
    right: $space-md;
    z-index: 5;
    background: $color-bg-paper;
    border: 1px solid $color-border;
    width: 36px;
    height: 36px;
    font-size: 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: $shadow-paper;

    &:hover {
      border-color: $una-gold;
    }
  }
</style>
