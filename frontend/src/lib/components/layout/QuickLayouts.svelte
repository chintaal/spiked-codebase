<script>
  import { activeLayout, layoutActions } from '$lib/stores/layouts.js';
  
  const quickLayouts = [
    { id: 'full-console', name: 'Full', icon: 'grid-3x3' },
    { id: 'focused-assistant', name: 'Focus', icon: 'layout-sidebar' },
    { id: 'conversation-only', name: 'Conv', icon: 'message-circle' },
    { id: 'assistant-only', name: 'AI', icon: 'sparkles' }
  ];
  
  function switchLayout(layoutId) {
    layoutActions.switchLayout(layoutId);
  }
  
  function getIcon(iconName) {
    switch (iconName) {
      case 'grid-3x3':
        return 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z';
      case 'layout-sidebar':
        return 'M3 3h7v18H3zM14 3h7v7h-7zM14 14h7v7h-7z';
      case 'message-circle':
        return 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z';
      case 'sparkles':
        return 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z';
      default:
        return 'M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z';
    }
  }
</script>

<div class="flex items-center space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg border border-gray-200 dark:border-gray-600">
  {#each quickLayouts as layout}
    <button
      class="px-2 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center space-x-1 {$activeLayout === layout.id ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
      on:click={() => switchLayout(layout.id)}
      title="Switch to {layout.name} layout"
    >
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        width="12" 
        height="12" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        stroke-width="2" 
        stroke-linecap="round" 
        stroke-linejoin="round"
      >
        <path d={getIcon(layout.icon)} />
      </svg>
      <span class="hidden sm:inline">{layout.name}</span>
    </button>
  {/each}
</div>
