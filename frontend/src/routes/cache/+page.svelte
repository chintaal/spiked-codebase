<script>
  import { onMount } from 'svelte';
  import { darkMode } from '$lib/stores/ui.js';

  // Svelte 5 runes
  let cacheStats = $state({});
  let canonicalQuestions = $state([]);
  let loading = $state(false);
  let refreshing = $state(false);
  let updating = $state(false);
  let clearing = $state(false);
  let message = $state('');
  let error = $state('');

  let refreshProgress = $state(0);
  let refreshStatus = $state('');
  let updateProgress = $state(0);
  let updateStatus = $state('');
  let lastRefreshTime = $state('');

  // Load initial data
  onMount(() => {
    loadCacheStats();
    loadCanonicalQuestions();
  });

  async function loadCacheStats() {
    try {
      loading = true;
      const response = await fetch('http://localhost:8000/api/cache/stats');
      const data = await response.json();
      
      if (response.ok) {
        cacheStats = data.cache_stats || {};
        if (data.cache_stats?.last_updated) {
          lastRefreshTime = new Date(data.cache_stats.last_updated).toLocaleString();
        }
      } else {
        error = data.detail || 'Failed to load cache stats';
      }
    } catch (err) {
      console.error('Error loading cache stats:', err);
      error = 'Network error while loading cache stats';
    } finally {
      loading = false;
    }
  }

  async function loadCanonicalQuestions() {
    try {
      const response = await fetch('http://localhost:8000/api/cache/canonical-questions');
      const data = await response.json();
      
      if (response.ok) {
        // Handle both string arrays and object arrays
        const questions = data.questions || [];
        const processedQuestions = questions.map(q => {
          if (typeof q === 'string') {
            return q;
          } else if (q && typeof q === 'object') {
            return q.question || q.text || q.query || JSON.stringify(q);
          }
          return String(q);
        });
        canonicalQuestions = processedQuestions;
      } else {
        error = data.detail || 'Failed to load canonical questions';
      }
    } catch (err) {
      console.error('Error loading canonical questions:', err);
      error = 'Network error while loading canonical questions';
    }
  }

  async function updateCache() {
    try {
      updating = true;
      updateProgress = 0;
      updateStatus = 'Checking for missing cache entries...';
      error = '';
      message = '';

      const response = await fetch('http://localhost:8000/api/cache/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      
      if (response.ok) {
        updateProgress = 100;
        updateStatus = 'Cache update completed!';
        
        const summary = data.summary || {};
        const totalCanonical = summary.total_canonical || 0;
        const alreadyCached = summary.already_cached || 0;
        const processed = summary.processed || 0;
        const successful = summary.successful || 0;
        const failed = summary.failed || 0;
        
        if (processed === 0) {
          message = `All ${totalCanonical} canonical questions are already cached with good confidence.`;
        } else {
          message = `Cache updated: ${successful} new entries added, ${alreadyCached} already cached (${totalCanonical} total canonical questions)`;
        }
        
        // Reload stats and questions
        await loadCacheStats();
        await loadCanonicalQuestions();
      } else {
        error = data.detail || 'Failed to update cache';
        updateStatus = 'Cache update failed';
      }
    } catch (err) {
      console.error('Error updating cache:', err);
      error = 'Network error during cache update';
      updateStatus = 'Cache update failed';
    } finally {
      updating = false;
      setTimeout(() => {
        updateProgress = 0;
        updateStatus = '';
      }, 3000);
    }
  }

  async function refreshCache() {
    try {
      refreshing = true;
      refreshProgress = 0;
      refreshStatus = 'Starting cache refresh...';
      error = '';
      message = '';

      const response = await fetch('http://localhost:8000/api/cache/batch-refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      
      if (response.ok) {
        refreshProgress = 100;
        refreshStatus = 'Cache refresh completed successfully!';
        message = `Successfully refreshed cache with ${data.summary?.successful || 0} questions`;
        
        // Reload stats
        await loadCacheStats();
      } else {
        error = data.detail || 'Failed to refresh cache';
        refreshStatus = 'Cache refresh failed';
      }
    } catch (err) {
      console.error('Error refreshing cache:', err);
      error = 'Network error during cache refresh';
      refreshStatus = 'Cache refresh failed';
    } finally {
      refreshing = false;
      setTimeout(() => {
        refreshProgress = 0;
        refreshStatus = '';
      }, 3000);
    }
  }

  async function clearCache() {
    if (!confirm('Are you sure you want to clear the entire cache? This action cannot be undone.')) {
      return;
    }

    try {
      clearing = true;
      error = '';
      message = '';

      const response = await fetch('http://localhost:8000/api/cache/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();
      
      if (response.ok) {
        message = 'Cache cleared successfully';
        // Reload stats
        await loadCacheStats();
      } else {
        error = data.detail || 'Failed to clear cache';
      }
    } catch (err) {
      console.error('Error clearing cache:', err);
      error = 'Network error while clearing cache';
    } finally {
      clearing = false;
    }
  }

  function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }
</script>

<svelte:head>
  <title>Cache Management - Spiked AI Console</title>
  <meta name="description" content="Manage the Spiked AI answer cache system" />
</svelte:head>

<div class={`h-screen flex flex-col bg-gray-50 dark:bg-gray-900 ${$darkMode ? 'dark' : ''}`}>
  <header class="h-16 px-6 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between shadow-sm">
    <div class="flex items-center space-x-3">
      <img src="/assets/logos/spikedlogo.webp" alt="Spiked AI Logo" class="h-10 w-auto" />
      <div class="h-8 w-px bg-gray-300 dark:bg-gray-600"></div>
      <h1 class="text-xl font-bold text-blue-600 dark:text-red-400">
        <span class="text-gray-800 dark:text-gray-100">Spiked</span>
        <span class="text-gray-600 dark:text-gray-300">AI</span>
        <span class="text-gray-500 dark:text-gray-400">Console</span>
        <span class="text-gray-400 dark:text-gray-500">v1.0</span>
      </h1>
    </div>
    <div class="flex-1 flex justify-center max-w-md">
      <nav class="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1.5 rounded-lg border border-gray-200 dark:border-gray-600">
        <a href="/console" class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Console</a>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Recordings</button>
        <button class="px-5 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500">Cache</button>
        <a href="/files" class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Files</a>
      </nav>
    </div>
    <div class="flex items-center space-x-4">
      <button 
        class="p-2.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600" 
        onclick={() => $darkMode = !$darkMode} 
        aria-label="Toggle dark mode"
      >
        {#if $darkMode}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-yellow-500">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-600 dark:text-gray-400">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 A7 7 0 0 0 21 12.79z"></path>
          </svg>
        {/if}
      </button>
      <div class="h-8 w-px bg-gray-300 dark:bg-gray-600"></div>
      <button class="h-10 w-10 rounded-lg bg-blue-600 text-white flex items-center justify-center text-sm font-bold hover:bg-blue-700 transition-colors" aria-label="User profile">
        CA
      </button>
    </div>
  </header>
  
  <div class="flex-1 p-6 gap-0 flex overflow-hidden">
    <div class="w-full max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="mb-8">
        <h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          🚀 Cache Management
        </h2>
        <p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
          Manage the Spiked AI answer cache system for zero-latency responses
        </p>
      </div>    <!-- Status Messages -->
    {#if message}
      <div class="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium text-green-800">{message}</p>
          </div>
        </div>
      </div>
    {/if}

    {#if error}
      <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium text-red-800">{error}</p>
          </div>
        </div>
      </div>
    {/if}

    <!-- Cache Statistics -->
    <section class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        📊 Cache Statistics
      </h2>
      
      {#if loading}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="animate-pulse flex space-x-4">
            <div class="rounded-full bg-gray-300 dark:bg-gray-600 h-10 w-10"></div>
            <div class="flex-1 space-y-2 py-1">
              <div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-3/4"></div>
              <div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                  <span class="text-blue-600 dark:text-blue-400 text-sm font-bold">Q</span>
                </div>
              </div>
              <div class="ml-4">
                <p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{cacheStats.total_cached_questions || 0}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">Cached Questions</p>
              </div>
            </div>
          </div>
          
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-green-500">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                  <span class="text-green-600 dark:text-green-400 text-sm font-bold">S</span>
                </div>
              </div>
              <div class="ml-4">
                <p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatFileSize(cacheStats.cache_file_size)}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">Cache Size</p>
              </div>
            </div>
          </div>
          
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-purple-500">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center">
                  <span class="text-purple-600 dark:text-purple-400 text-sm font-bold">T</span>
                </div>
              </div>
              <div class="ml-4">
                <p class="text-sm font-bold text-gray-900 dark:text-gray-100">{lastRefreshTime || 'Never'}</p>
                <p class="text-sm text-gray-600 dark:text-gray-400">Last Updated</p>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </section>

    <!-- Cache Actions -->
    <section class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        🔧 Cache Actions
      </h2>
      
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <!-- Update Cache -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-yellow-500">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
            🔄 Update Cache
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Intelligently add missing canonical questions to cache without regenerating existing entries
          </p>
          
          {#if updating}
            <div class="mb-4">
              <div class="bg-gray-200 dark:bg-gray-600 rounded-full h-2 mb-2">
                <div class="bg-yellow-600 h-2 rounded-full transition-all duration-300" style="width: {updateProgress}%"></div>
              </div>
              <p class="text-xs text-gray-600 dark:text-gray-400">{updateStatus}</p>
            </div>
            <button class="w-full bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 py-2 px-4 rounded-lg cursor-not-allowed flex items-center justify-center gap-2" disabled>
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 dark:border-gray-400"></div>
              Updating...
            </button>
          {:else}
            <button class="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded-lg font-medium transition-colors" onclick={updateCache}>
              🔄 Update Cache
            </button>
          {/if}
        </div>

        <!-- Refresh Cache -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
            🔄 Refresh Cache
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Populate cache with responses from canonical questions using the /analyze endpoint
          </p>
          
          {#if refreshing}
            <div class="mb-4">
              <div class="bg-gray-200 dark:bg-gray-600 rounded-full h-2 mb-2">
                <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: {refreshProgress}%"></div>
              </div>
              <p class="text-xs text-gray-600 dark:text-gray-400">{refreshStatus}</p>
            </div>
            <button class="w-full bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 py-2 px-4 rounded-lg cursor-not-allowed flex items-center justify-center gap-2" disabled>
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 dark:border-gray-400"></div>
              Refreshing...
            </button>
          {:else}
            <button class="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-medium transition-colors" onclick={refreshCache}>
              🔄 Refresh Cache
            </button>
          {/if}
        </div>

        <!-- Clear Cache -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-red-500">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
            🗑️ Clear Cache
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Remove all cached answers. This will require a refresh to restore performance benefits.
          </p>
          
          <button 
            class="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg font-medium transition-colors disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center justify-center gap-2" 
            onclick={clearCache}
            disabled={clearing}
          >
            {#if clearing}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
              Clearing...
            {:else}
              🗑️ Clear Cache
            {/if}
          </button>
        </div>

        <!-- Reload Stats -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border-l-4 border-green-500">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
            📈 Reload Stats
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Refresh the cache statistics and status information
          </p>
          
          <button class="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg font-medium transition-colors" onclick={loadCacheStats}>
            📈 Reload Stats
          </button>
        </div>
      </div>
    </section>

    <!-- Canonical Questions -->
    <section class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        📋 Canonical Questions
      </h2>
      <p class="text-gray-600 dark:text-gray-400 mb-6">
        These questions are used to populate the cache during refresh operations
      </p>
      
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        {#if canonicalQuestions.length > 0}
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <span class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Total Questions: <span class="text-blue-600 dark:text-blue-400">{canonicalQuestions.length}</span>
              </span>
              <button class="bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 text-blue-700 dark:text-blue-300 px-3 py-1 rounded-lg text-sm font-medium transition-colors" onclick={loadCanonicalQuestions}>
                🔄 Reload Questions
              </button>
            </div>
          </div>
          
          <div class="max-h-96 overflow-y-auto">
            {#each canonicalQuestions as question, index}
              <div class="px-6 py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <div class="flex items-start gap-3">
                  <div class="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                    <span class="text-blue-600 dark:text-blue-400 text-sm font-bold">{index + 1}</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-gray-900 dark:text-gray-100 text-sm leading-relaxed break-words">{question}</p>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="px-6 py-12 text-center">
            <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
              <svg class="w-8 h-8 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <p class="text-gray-500 dark:text-gray-400 mb-4">No canonical questions loaded</p>
            <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors" onclick={loadCanonicalQuestions}>
              🔄 Reload Questions
            </button>
          </div>
        {/if}
      </div>
    </section>

    <!-- Performance Information -->
    <section class="mb-8">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        ⚡ Performance Benefits
      </h2>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border border-green-200">
          <div class="text-center">
            <div class="w-12 h-12 mx-auto mb-3 bg-green-500 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Cached Questions</h3>
            <div class="text-2xl font-bold text-green-600 mb-1">5-10ms</div>
            <div class="text-sm text-green-700 font-medium">98% faster</div>
          </div>
        </div>
        
        <div class="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
          <div class="text-center">
            <div class="w-12 h-12 mx-auto mb-3 bg-blue-500 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Similar Questions</h3>
            <div class="text-2xl font-bold text-blue-600 mb-1">15-25ms</div>
            <div class="text-sm text-blue-700 font-medium">95% faster</div>
          </div>
        </div>
        
        <div class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
          <div class="text-center">
            <div class="w-12 h-12 mx-auto mb-3 bg-purple-500 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">New Questions</h3>
            <div class="text-2xl font-bold text-purple-600 mb-1">300-500ms</div>
            <div class="text-sm text-purple-700 font-medium">Full RAG pipeline</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</div>
</div>