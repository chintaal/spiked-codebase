<script>
  import { currentLayoutConfig, layoutActions, isCustomLayout, activeLayout } from '$lib/stores/layouts.js';
  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher();
  
  $: components = $currentLayoutConfig?.components || {};
  $: isCustom = isCustomLayout($activeLayout);
  
  function toggleComponent(componentName) {
    layoutActions.toggleComponent(componentName);
    dispatch('componentToggled', { componentName });
  }
  
  function getComponentIcon(componentName) {
    switch (componentName) {
      case 'conversation':
        return 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z';
      case 'assistant':
        return 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423L16.5 15.75l.394 1.183a2.25 2.25 0 001.423 1.423L19.5 18.75l-1.183.394a2.25 2.25 0 00-1.423 1.423z';
      case 'analytics':
        return 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z';
      default:
        return 'M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z';
    }
  }
  
  function getComponentName(componentName) {
    switch (componentName) {
      case 'conversation':
        return 'Conversation';
      case 'assistant':
        return 'AI Assistant';
      case 'analytics':
        return 'Analytics';
      default:
        return componentName;
    }
  }
  
  function getComponentDescription(componentName) {
    switch (componentName) {
      case 'conversation':
        return 'Transcription and conversation panel';
      case 'assistant':
        return 'AI-powered question answering';
      case 'analytics':
        return 'Real-time analytics and insights';
      default:
        return 'Console component';
    }
  }
</script>

<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">Panel Controls</h3>
    {#if !isCustom}
      <span class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full">
        Read Only
      </span>
    {/if}
  </div>
  
  <div class="space-y-3">
    {#each Object.entries(components) as [componentName, config]}
      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              stroke-width="1.5" 
              stroke-linecap="round" 
              stroke-linejoin="round"
              class="text-gray-600 dark:text-gray-400"
            >
              <path d={getComponentIcon(componentName)} />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
              {getComponentName(componentName)}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">
              {getComponentDescription(componentName)}
            </div>
          </div>
        </div>
        
        <div class="flex items-center space-x-3">
          {#if config.enabled}
            <div class="text-xs text-gray-500 dark:text-gray-400 min-w-0">
              {Math.round(config.width)}%
            </div>
          {/if}
          
          <button
            class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 {config.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'} {!isCustom ? 'opacity-50 cursor-not-allowed' : ''}"
            role="switch"
            aria-checked={config.enabled}
            aria-label="Toggle {getComponentName(componentName)}"
            disabled={!isCustom}
            on:click={() => isCustom && toggleComponent(componentName)}
          >
            <span 
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out {config.enabled ? 'translate-x-5' : 'translate-x-0'}"
            ></span>
          </button>
        </div>
      </div>
    {/each}
  </div>
  
  {#if !isCustom}
    <div class="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
      <div class="flex items-start space-x-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5">
          <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
        </svg>
        <div>
          <p class="text-xs font-medium text-amber-800 dark:text-amber-200">
            Default Layout
          </p>
          <p class="text-xs text-amber-700 dark:text-amber-300 mt-1">
            To customize panels, duplicate this layout or create a new one.
          </p>
        </div>
      </div>
    </div>
  {/if}
</div>
