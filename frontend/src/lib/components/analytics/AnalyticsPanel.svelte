<script>
  import { questionsStore } from '$lib/stores/questions.js';
  import { darkMode } from '$lib/stores/ui.js';
</script>

<div class="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200 dark:bg-gray-800 dark:border-gray-700">
  <!-- Header -->
  <div class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
    <div class="flex items-center space-x-3">
      <div class="p-2 bg-green-600 rounded-lg">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
          <path d="M3 3v5h5"/>
          <path d="M6 17l4-4 4 4 6-6"/>
          <path d="M21 21v-5h-5"/>
        </svg>
      </div>
      <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">Knowledge Analytics</h2>
    </div>
  </div>
  
  <div class="flex-1 overflow-y-auto p-6">
    <!-- Key Metrics Section -->
    <div class="mb-8">
      <div class="grid grid-cols-1 gap-4 mb-6">
        <!-- Total Queries Card -->
        <div class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 p-5 rounded-lg border border-blue-200 dark:border-blue-700">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-blue-700 dark:text-blue-300 mb-1">Total Queries</div>
              <div class="text-3xl font-bold text-blue-900 dark:text-blue-100">{$questionsStore.questions.length}</div>
            </div>
            <div class="p-3 bg-blue-600 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
          </div>
        </div>
        
        <!-- Topics Covered Card -->
        <div class="bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 p-5 rounded-lg border border-green-200 dark:border-green-700">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-green-700 dark:text-green-300 mb-1">Topics Covered</div>
              <div class="text-3xl font-bold text-green-900 dark:text-green-100">
                {new Set($questionsStore.questions.map(q => q.intent).filter(Boolean)).size}
              </div>
            </div>
            <div class="p-3 bg-green-600 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
          </div>
        </div>
        
        <!-- Knowledge Gaps Card -->
        <div class="bg-gradient-to-r from-orange-50 to-orange-100 dark:from-orange-900/30 dark:to-orange-800/30 p-5 rounded-lg border border-orange-200 dark:border-orange-700">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium text-orange-700 dark:text-orange-300 mb-1">Knowledge Gaps</div>
              <div class="text-3xl font-bold text-orange-900 dark:text-orange-100">
                {$questionsStore.questions.filter(q => q.informationGap).length}
              </div>
            </div>
            <div class="p-3 bg-orange-600 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 8v4"/>
                <path d="M12 16h.01"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Query Analysis Section -->
    <div class="mb-8">
      <div class="flex items-center space-x-2 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-600 dark:text-gray-400">
          <path d="M3 3v5h5"/>
          <path d="M6 17l4-4 4 4 6-6"/>
        </svg>
        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200">Query Analysis</h3>
      </div>
      
      {#if $questionsStore.questions.length === 0}
        <div class="bg-gray-50 dark:bg-gray-700 p-8 rounded-lg text-center border border-gray-200 dark:border-gray-600">
          <div class="p-4 bg-gray-100 dark:bg-gray-600 rounded-lg mb-4 inline-block">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-500 dark:text-gray-400">
              <path d="M3 3v5h5"/>
              <path d="M6 17l4-4 4 4 6-6"/>
            </svg>
          </div>
          <h4 class="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No Data Available</h4>
          <p class="text-gray-500 dark:text-gray-400 text-sm">Start asking questions to generate analytics and insights.</p>
        </div>
      {:else}
        <div class="space-y-6">
          <!-- Top Intents -->
          <div class="bg-white dark:bg-gray-700 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600">
            <div class="flex items-center space-x-2 mb-4">
              <div class="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-600 dark:text-purple-400">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <div>
                <h4 class="font-semibold text-gray-800 dark:text-gray-200">Top Query Intents</h4>
                <p class="text-sm text-gray-500 dark:text-gray-400">Most common question types</p>
              </div>
            </div>
            <div class="text-gray-800 dark:text-gray-200 font-medium">
              {Array.from(new Set($questionsStore.questions.map(q => q.intent).filter(Boolean))).slice(0, 3).join(', ') || 'None detected yet'}
            </div>
          </div>
          
          <!-- Sentiment Analysis -->
          <div class="bg-white dark:bg-gray-700 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600">
            <div class="flex items-center space-x-2 mb-4">
              <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                  <line x1="9" y1="9" x2="9.01" y2="9"/>
                  <line x1="15" y1="9" x2="15.01" y2="9"/>
                </svg>
              </div>
              <div>
                <h4 class="font-semibold text-gray-800 dark:text-gray-200">Sentiment Breakdown</h4>
                <p class="text-sm text-gray-500 dark:text-gray-400">Emotional tone of queries</p>
              </div>
            </div>
            <div class="grid grid-cols-1 gap-3">
              {#each ['positive', 'neutral', 'negative'] as sentiment}
                {@const count = $questionsStore.questions.filter(q => q.sentiment?.toLowerCase() === sentiment).length}
                <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-600 rounded-lg">
                  <div class="flex items-center space-x-3">
                    <div class="w-4 h-4 rounded-full 
                      {sentiment === 'positive' ? 'bg-green-500' : 
                       sentiment === 'negative' ? 'bg-red-500' : 'bg-yellow-500'}">
                    </div>
                    <span class="font-medium text-gray-700 dark:text-gray-300 capitalize">{sentiment}</span>
                  </div>
                  <span class="text-lg font-bold text-gray-800 dark:text-gray-200">{count}</span>
                </div>
              {/each}
            </div>
          </div>
          
          <!-- Sources Usage -->
          <div class="bg-white dark:bg-gray-700 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600">
            <div class="flex items-center space-x-2 mb-4">
              <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-indigo-600 dark:text-indigo-400">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10,9 9,9 8,9"/>
                </svg>
              </div>
              <div>
                <h4 class="font-semibold text-gray-800 dark:text-gray-200">Average Sources per Query</h4>
                <p class="text-sm text-gray-500 dark:text-gray-400">Information source utilization</p>
              </div>
            </div>
            <div class="text-3xl font-bold text-gray-800 dark:text-gray-200">
              {($questionsStore.questions.reduce((acc, q) => acc + (q.sources?.length || 0), 0) / 
                Math.max($questionsStore.questions.length, 1)).toFixed(1)}
            </div>
          </div>
        </div>
      {/if}
    </div>
    
    <!-- Knowledge Gaps Section -->
    <div>
      <div class="flex items-center space-x-2 mb-6">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-orange-600 dark:text-orange-400">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4"/>
          <path d="M12 16h.01"/>
        </svg>
        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200">Recent Knowledge Gaps</h3>
      </div>
      
      {#if $questionsStore.questions.filter(q => q.informationGap).length === 0}
        <div class="bg-green-50 dark:bg-green-900/20 p-8 rounded-lg text-center border border-green-200 dark:border-green-700">
          <div class="p-4 bg-green-100 dark:bg-green-800/30 rounded-lg mb-4 inline-block">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600 dark:text-green-400">
              <path d="M9 12l2 2 4-4"/>
              <circle cx="12" cy="12" r="10"/>
            </svg>
          </div>
          <h4 class="text-lg font-medium text-green-700 dark:text-green-300 mb-2">No Knowledge Gaps</h4>
          <p class="text-green-600 dark:text-green-400 text-sm">All queries have been successfully addressed with available information.</p>
        </div>
      {:else}
        <div class="space-y-4">
          {#each $questionsStore.questions.filter(q => q.informationGap).slice(-3) as question, index}
            <div class="bg-white dark:bg-gray-700 p-5 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600 border-l-4 border-l-orange-500">
              <div class="flex items-start space-x-4">
                <div class="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-orange-100 dark:bg-orange-900/30 rounded-full">
                  <span class="text-orange-600 dark:text-orange-400 font-semibold text-sm">{index + 1}</span>
                </div>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2">{question.text}</h4>
                  <p class="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-600 p-3 rounded-lg">{question.informationGap}</p>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>