<script>
  import { availableLayouts, activeLayout, layoutActions, isCustomLayout } from '$lib/stores/layouts.js';
  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher();
  
  export let show = false;
  
  let selectedLayoutId = $activeLayout;
  let showCreateForm = false;
  let showDeleteConfirm = null;
  
  // New layout form data
  let newLayoutName = '';
  let newLayoutDescription = '';
  let newLayoutComponents = {
    conversation: { enabled: true, width: 35 },
    assistant: { enabled: true, width: 50 },
    analytics: { enabled: true, width: 15 }
  };
  
  $: layouts = Object.values($availableLayouts);
  $: selectedLayout = $availableLayouts[selectedLayoutId];
  $: isSelectedCustom = isCustomLayout(selectedLayoutId);
  
  function close() {
    show = false;
    dispatch('close');
  }
  
  function selectLayout(layoutId) {
    selectedLayoutId = layoutId;
    layoutActions.switchLayout(layoutId);
  }
  
  function duplicateLayout() {
    if (!selectedLayout) return;
    
    const newId = layoutActions.duplicateLayout(selectedLayoutId, `${selectedLayout.name} Copy`);
    if (newId) {
      selectedLayoutId = newId;
      layoutActions.switchLayout(newId);
    }
  }
  
  function deleteLayout() {
    if (!isSelectedCustom) return;
    
    layoutActions.deleteLayout(selectedLayoutId);
    selectedLayoutId = 'full-console';
    showDeleteConfirm = null;
  }
  
  function createNewLayout() {
    if (!newLayoutName.trim()) return;
    
    const newId = `custom-${Date.now()}`;
    layoutActions.createLayout({
      id: newId,
      name: newLayoutName.trim(),
      description: newLayoutDescription.trim() || 'Custom layout',
      components: { ...newLayoutComponents },
      modes: ['microphone', 'meeting']
    });
    
    selectedLayoutId = newId;
    layoutActions.switchLayout(newId);
    
    // Reset form
    newLayoutName = '';
    newLayoutDescription = '';
    newLayoutComponents = {
      conversation: { enabled: true, width: 35 },
      assistant: { enabled: true, width: 50 },
      analytics: { enabled: true, width: 15 }
    };
    showCreateForm = false;
  }
  
  function toggleNewLayoutComponent(componentName) {
    newLayoutComponents[componentName].enabled = !newLayoutComponents[componentName].enabled;
    
    // If disabling, set width to 0
    if (!newLayoutComponents[componentName].enabled) {
      newLayoutComponents[componentName].width = 0;
    } else {
      // If enabling and width is 0, give it a default width
      if (newLayoutComponents[componentName].width === 0) {
        const defaultWidth = componentName === 'conversation' ? 30 : 
                           componentName === 'assistant' ? 50 : 20;
        newLayoutComponents[componentName].width = defaultWidth;
      }
    }
    
    // Normalize widths
    const enabledComponents = Object.entries(newLayoutComponents).filter(([_, config]) => config.enabled);
    const totalWidth = enabledComponents.reduce((sum, [_, config]) => sum + config.width, 0);
    
    if (totalWidth > 0 && enabledComponents.length > 0) {
      enabledComponents.forEach(([component, config]) => {
        newLayoutComponents[component].width = (config.width / totalWidth) * 100;
      });
    }
  }
  
  function resetToDefaults() {
    if (confirm('This will delete all custom layouts and reset to defaults. Are you sure?')) {
      layoutActions.resetToDefaults();
      selectedLayoutId = 'full-console';
      showDeleteConfirm = null;
    }
  }
  
  function getComponentIcon(componentName) {
    switch (componentName) {
      case 'conversation':
        return 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z';
      case 'assistant':
        return 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z';
      case 'analytics':
        return 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z';
      default:
        return 'M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z';
    }
  }
</script>

{#if show}
  <div 
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" 
    role="dialog" 
    aria-modal="true"
    tabindex="-1"
    on:click={() => !showDeleteConfirm && close()}
    on:keydown={(e) => e.key === 'Escape' && !showDeleteConfirm && close()}
  >
    <div 
      class="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
      on:click|stopPropagation
      role="none"
    >
      <!-- Header -->
      <div class="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Layout Manager</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Configure your console layouts and panel arrangements
          </p>
        </div>
        <button
          class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          on:click={close}
          aria-label="Close layout manager"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      
      <!-- Content -->
      <div class="flex-1 overflow-hidden flex">
        <!-- Layout List -->
        <div class="w-1/3 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
          <div class="p-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Available Layouts</h3>
              <button
                class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                on:click={() => showCreateForm = !showCreateForm}
              >
                {showCreateForm ? 'Cancel' : 'New'}
              </button>
            </div>
            
            <!-- Create New Layout Form -->
            {#if showCreateForm}
              <div class="mb-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Create New Layout</h4>
                
                <div class="space-y-3">
                  <div>
                    <label for="layout-name" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Layout Name
                    </label>
                    <input
                      id="layout-name"
                      type="text"
                      bind:value={newLayoutName}
                      placeholder="My Custom Layout"
                      class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label for="layout-description" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Description (optional)
                    </label>
                    <input
                      id="layout-description"
                      type="text"
                      bind:value={newLayoutDescription}
                      placeholder="Layout description"
                      class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <fieldset>
                    <legend class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Enabled Panels
                    </legend>
                    <div class="space-y-2">
                      {#each Object.entries(newLayoutComponents) as [componentName, config]}
                        <label class="flex items-center">
                          <input
                            type="checkbox"
                            checked={config.enabled}
                            on:change={() => toggleNewLayoutComponent(componentName)}
                            class="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                          />
                          <span class="ml-2 text-sm text-gray-700 dark:text-gray-300 capitalize">
                            {componentName}
                          </span>
                          {#if config.enabled}
                            <span class="ml-auto text-xs text-gray-500 dark:text-gray-400">
                              {Math.round(config.width)}%
                            </span>
                          {/if}
                        </label>
                      {/each}
                    </div>
                  </fieldset>
                  
                  <button
                    class="w-full px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!newLayoutName.trim()}
                    on:click={createNewLayout}
                  >
                    Create Layout
                  </button>
                </div>
              </div>
            {/if}
            
            <!-- Layout List -->
            <div class="space-y-2">
              {#each layouts as layout}
                <button
                  class="w-full text-left p-3 rounded-lg border transition-colors {selectedLayoutId === layout.id ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50'}"
                  on:click={() => selectLayout(layout.id)}
                >
                  <div class="flex items-start justify-between">
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center space-x-2">
                        <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {layout.name}
                        </span>
                        {#if isCustomLayout(layout.id)}
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-500">
                            <path d="M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z"/>
                          </svg>
                        {/if}
                      </div>
                      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {layout.description}
                      </p>
                    </div>
                    <div class="flex items-center space-x-1 ml-2">
                      {#each Object.entries(layout.components) as [component, config]}
                        <div class="w-2 h-2 rounded-full {config.enabled ? 'bg-green-400' : 'bg-gray-300 dark:bg-gray-600'}"></div>
                      {/each}
                    </div>
                  </div>
                </button>
              {/each}
            </div>
          </div>
        </div>
        
        <!-- Layout Details -->
        <div class="flex-1 overflow-y-auto">
          {#if selectedLayout}
            <div class="p-6">
              <div class="flex items-center justify-between mb-6">
                <div>
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center space-x-2">
                    <span>{selectedLayout.name}</span>
                    {#if isSelectedCustom}
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-500">
                        <path d="M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z"/>
                      </svg>
                    {/if}
                  </h3>
                  <p class="text-sm text-gray-600 dark:text-gray-400">
                    {selectedLayout.description}
                  </p>
                </div>
                
                <div class="flex items-center space-x-2">
                  <button
                    class="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    on:click={duplicateLayout}
                  >
                    Duplicate
                  </button>
                  
                  {#if isSelectedCustom}
                    <button
                      class="px-3 py-1.5 text-sm border border-red-300 dark:border-red-600 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      on:click={() => showDeleteConfirm = selectedLayoutId}
                    >
                      Delete
                    </button>
                  {/if}
                </div>
              </div>
              
              <!-- Component Configuration -->
              <div class="space-y-4">
                <h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Panel Configuration</h4>
                
                <div class="grid gap-4">
                  {#each Object.entries(selectedLayout.components) as [componentName, config]}
                    <div class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg {config.enabled ? 'bg-green-50 dark:bg-green-900/10' : 'bg-gray-50 dark:bg-gray-700/50'}">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                          <svg 
                            xmlns="http://www.w3.org/2000/svg" 
                            width="20" 
                            height="20" 
                            viewBox="0 0 24 24" 
                            fill="none" 
                            stroke="currentColor" 
                            stroke-width="2" 
                            stroke-linecap="round" 
                            stroke-linejoin="round"
                            class="text-gray-600 dark:text-gray-400"
                          >
                            <path d={getComponentIcon(componentName)} />
                          </svg>
                          <div>
                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
                              {componentName} Panel
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                              {config.enabled ? `Width: ${Math.round(config.width)}%` : 'Disabled'}
                            </div>
                          </div>
                        </div>
                        
                        <div class="flex items-center space-x-2">
                          <span class="text-xs font-medium {config.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}">
                            {config.enabled ? 'Enabled' : 'Disabled'}
                          </span>
                          <div class="w-3 h-3 rounded-full {config.enabled ? 'bg-green-400' : 'bg-gray-300 dark:bg-gray-600'}"></div>
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>
      
      <!-- Footer -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <button
          class="px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          on:click={resetToDefaults}
        >
          Reset to Defaults
        </button>
        
        <div class="flex items-center space-x-3">
          <button
            class="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            on:click={close}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm}
  <div 
    class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-60" 
    role="dialog" 
    aria-modal="true"
    tabindex="-1"
  >
    <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Delete Layout</h3>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Are you sure you want to delete "{$availableLayouts[showDeleteConfirm]?.name}"? This action cannot be undone.
      </p>
      <div class="flex justify-end space-x-3">
        <button
          class="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          on:click={() => showDeleteConfirm = null}
        >
          Cancel
        </button>
        <button
          class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          on:click={deleteLayout}
        >
          Delete
        </button>
      </div>
    </div>
  </div>
{/if}
