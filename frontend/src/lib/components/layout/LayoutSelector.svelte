<script>
  import { availableLayouts, activeLayout, layoutActions } from '$lib/stores/layouts.js';
  import LayoutManager from './LayoutManager.svelte';
  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher();
  
  let showDropdown = false;
  let showLayoutManager = false;
  
  $: layouts = Object.values($availableLayouts);
  
  function selectLayout(layoutId) {
    layoutActions.switchLayout(layoutId);
    showDropdown = false;
    dispatch('layoutChanged', { layoutId });
  }
  
  function toggleDropdown() {
    showDropdown = !showDropdown;
  }
  
  function openLayoutManager() {
    showLayoutManager = true;
    showDropdown = false;
  }
  
  // Close dropdown when clicking outside
  function handleClickOutside(event) {
    if (!event.target.closest('.layout-selector')) {
      showDropdown = false;
    }
  }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="layout-selector relative">
  <button 
    class="px-3 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600 flex items-center space-x-2"
    on:click={toggleDropdown}
    aria-label="Select layout"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
      <line x1="9" y1="9" x2="21" y2="9"/>
      <line x1="9" y1="15" x2="21" y2="15"/>
      <line x1="3" y1="9" x2="5" y2="9"/>
      <line x1="3" y1="15" x2="5" y2="15"/>
    </svg>
    <span class="hidden sm:inline">Layout</span>
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="transition-transform {showDropdown ? 'rotate-180' : ''}">
      <polyline points="6,9 12,15 18,9"/>
    </svg>
  </button>
  
  {#if showDropdown}
    <div class="absolute top-full left-0 mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
      <div class="p-3 border-b border-gray-200 dark:border-gray-600">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Console Layouts</h3>
        <p class="text-xs text-gray-500 dark:text-gray-400">Choose how your console is organized</p>
      </div>
      
      <div class="p-2">
        <!-- Default Layouts -->
        <div class="mb-3">
          <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide px-2 py-1">
            Default Layouts
          </div>
          {#each layouts.filter(layout => !layout.id.includes('custom')) as layout}
            <button
              class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-start space-x-3 {$activeLayout === layout.id ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700' : ''}"
              on:click={() => selectLayout(layout.id)}
            >
              <div class="flex-shrink-0 mt-0.5">
                {#if $activeLayout === layout.id}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
                    <polyline points="20,6 9,17 4,12"/>
                  </svg>
                {:else}
                  <div class="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600"></div>
                {/if}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {layout.name}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {layout.description}
                </div>
                <div class="flex items-center space-x-1 mt-1">
                  {#each Object.entries(layout.components) as [component, config]}
                    {#if config.enabled}
                      <div class="w-2 h-2 rounded-full bg-green-400"></div>
                    {:else}
                      <div class="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                    {/if}
                  {/each}
                </div>
              </div>
            </button>
          {/each}
        </div>
        
        <!-- Custom Layouts -->
        {#if layouts.some(layout => layout.id.includes('custom'))}
          <div class="mb-3">
            <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide px-2 py-1">
              Custom Layouts
            </div>
            {#each layouts.filter(layout => layout.id.includes('custom')) as layout}
              <button
                class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-start space-x-3 {$activeLayout === layout.id ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700' : ''}"
                on:click={() => selectLayout(layout.id)}
              >
                <div class="flex-shrink-0 mt-0.5">
                  {#if $activeLayout === layout.id}
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
                      <polyline points="20,6 9,17 4,12"/>
                    </svg>
                  {:else}
                    <div class="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600"></div>
                  {/if}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center">
                    {layout.name}
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ml-1 text-purple-500">
                      <path d="M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z"/>
                    </svg>
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {layout.description}
                  </div>
                  <div class="flex items-center space-x-1 mt-1">
                    {#each Object.entries(layout.components) as [component, config]}
                      {#if config.enabled}
                        <div class="w-2 h-2 rounded-full bg-purple-400"></div>
                      {:else}
                        <div class="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                      {/if}
                    {/each}
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
      
      <div class="p-2 border-t border-gray-200 dark:border-gray-600">
        <button
          class="w-full px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors flex items-center justify-center space-x-2"
          on:click={openLayoutManager}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
          <span>Manage Layouts</span>
        </button>
      </div>
    </div>
  {/if}
</div>

<!-- Layout Manager Modal -->
<LayoutManager bind:show={showLayoutManager} on:close={() => showLayoutManager = false} />

<style>
  .layout-selector {
    position: relative;
  }
  
  /* Custom scrollbar for dropdown */
  .max-h-96::-webkit-scrollbar {
    width: 6px;
  }
  
  .max-h-96::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .max-h-96::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
  }
  
  .max-h-96::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
  }
</style>
