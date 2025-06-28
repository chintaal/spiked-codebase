<script>
  import { whisperStore } from '$lib/stores/whisperStore.js';
  import { questionsStore } from '$lib/stores/questions.js';
  
  function countQuestionsInTranscript() {
    return $whisperStore.messages.filter(m => m.text.includes('?')).length;
  }
  
  function calculateAverageMessageLength() {
    if ($whisperStore.messages.length === 0) return 0;
    return Math.round($whisperStore.messages.reduce((sum, m) => sum + m.text.length, 0) / $whisperStore.messages.length);
  }
  
  function getDetectionAccuracy() {
    // Simple estimation based on detected vs explicit questions
    const explicitQuestions = $whisperStore.messages.filter(m => m.text.includes('?')).length;
    const detectedQuestions = $whisperStore.detectedQuestions.length;
    
    if (explicitQuestions === 0) return detectedQuestions > 0 ? '100%' : 'N/A';
    return `${Math.min(100, Math.round((detectedQuestions / explicitQuestions) * 100))}%`;
  }
  
  function getRespondedQuestionPercentage() {
    const totalQuestions = $questionsStore.questions.length;
    const answeredQuestions = $questionsStore.questions.filter(q => q.answer).length;
    
    if (totalQuestions === 0) return 'N/A';
    return `${Math.round((answeredQuestions / totalQuestions) * 100)}%`;
  }
  
  function getUndetectedQuestionsCount() {
    // This is a simple heuristic - questions in transcript with ? that weren't detected
    const explicitQuestions = $whisperStore.messages
      .filter(m => m.text.includes('?'))
      .length;
    
    const detectedQuestions = $whisperStore.detectedQuestions.length;
    
    return Math.max(0, explicitQuestions - detectedQuestions);
  }
  
  function getMostRecentQuestion() {
    if ($whisperStore.detectedQuestions.length === 0) return null;
    
    // Sort by timestamp and get the most recent
    return [...$whisperStore.detectedQuestions]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];
  }
  
  function formatTime(timestamp) {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return "";
    }
  }
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-xl overflow-hidden">
  <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30">
    <div class="flex items-center">
      <div class="flex-shrink-0 w-8 h-8 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center shadow-sm mr-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      </div>
      <div>
        <h2 class="text-lg font-semibold bg-clip-text text-transparent bg-gradient-to-r from-indigo-700 to-purple-700 dark:from-indigo-400 dark:to-purple-400">Analytics Dashboard</h2>
        <p class="text-xs text-gray-600 dark:text-gray-400">
          Real-time metrics from your sales conversation
        </p>
      </div>
    </div>
  </div>
  
  <div class="p-4 overflow-y-auto bg-gradient-to-b from-gray-50/50 to-white dark:from-gray-800/50 dark:to-gray-800">
    <!-- Stats Cards -->
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div class="p-3 bg-gradient-to-br from-white to-gray-50 dark:from-gray-700 dark:to-gray-700/80 rounded-lg shadow-sm text-center border border-gray-100 dark:border-gray-600 hover:shadow-md transition-all duration-300">
        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Messages</div>
        <div class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">{$whisperStore.messages.length}</div>
      </div>
      
      <div class="p-3 bg-gradient-to-br from-white to-gray-50 dark:from-gray-700 dark:to-gray-700/80 rounded-lg shadow-sm text-center border border-gray-100 dark:border-gray-600 hover:shadow-md transition-all duration-300">
        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Questions</div>
        <div class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400">
          {$whisperStore.detectedQuestions.length}
        </div>
      </div>
      
      <div class="p-3 bg-gradient-to-br from-white to-gray-50 dark:from-gray-700 dark:to-gray-700/80 rounded-lg shadow-sm text-center border border-gray-100 dark:border-gray-600 hover:shadow-md transition-all duration-300">
        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">AI Answers</div>
        <div class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400">{$questionsStore.questions.filter(q => q.answer).length}</div>
      </div>
    </div>
    
    <!-- Key Metrics Section -->
    <div class="mb-5">
      <h3 class="text-sm font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300 mb-3 flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5 text-indigo-500 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        Key Metrics
      </h3>
      
      {#if $whisperStore.messages.length === 0}
        <div class="py-10 text-center text-gray-400 dark:text-gray-500 italic text-sm bg-gradient-to-br from-gray-50 to-white dark:from-gray-700/70 dark:to-gray-800/70 rounded-xl border border-dashed border-gray-200 dark:border-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto mb-3 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>No conversation data available yet</p>
          <p class="mt-1">Start recording to generate analytics</p>
        </div>
      {:else}
        <div class="bg-white dark:bg-gray-700 rounded-xl shadow-sm border border-gray-100 dark:border-gray-600 divide-y divide-gray-100 dark:divide-gray-600 overflow-hidden">
          <div class="flex justify-between items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-600/50 transition-colors duration-200">
            <div class="flex items-center text-sm text-gray-600 dark:text-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2 text-indigo-500 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              Avg. Message Length
            </div>
            <div class="font-medium text-sm px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/30">
              {calculateAverageMessageLength()} chars
            </div>
          </div>
          
          <div class="flex justify-between items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-600/50 transition-colors duration-200">
            <div class="flex items-center text-sm text-gray-600 dark:text-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2 text-purple-500 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Question Detection
            </div>
            <div class="font-medium text-sm px-2.5 py-1 rounded-full bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 border border-purple-100 dark:border-purple-900/30">
              {getDetectionAccuracy()}
            </div>
          </div>
          
          <div class="flex justify-between items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-600/50 transition-colors duration-200">
            <div class="flex items-center text-sm text-gray-600 dark:text-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2 text-pink-500 dark:text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              AI Response Rate
            </div>
            <div class="font-medium text-sm px-2.5 py-1 rounded-full bg-pink-50 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400 border border-pink-100 dark:border-pink-900/30">
              {$whisperStore.detectedQuestions.length > 0 
                ? `${Math.round(($whisperStore.detectedQuestions.filter(q => q.answered).length / $whisperStore.detectedQuestions.length) * 100)}%` 
                : 'N/A'}
            </div>
          </div>
        </div>
      {/if}
    </div>
    
    <!-- Top Questions Section -->
    <div class="mb-4">
      <h3 class="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">Detected Questions</h3>
      
      {#if $whisperStore.detectedQuestions.length === 0}
        <div class="py-5 text-center text-gray-400 dark:text-gray-500 italic text-sm bg-gray-50 dark:bg-gray-700/70 rounded-lg border border-gray-100 dark:border-gray-600">
          No questions detected in the conversation yet.
        </div>
      {:else}
        <ul class="bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-100 dark:border-gray-600 divide-y divide-gray-100 dark:divide-gray-600">
          {#each $whisperStore.detectedQuestions.slice(-5).reverse() as question}
            <li class="p-3">
              <div class="text-sm text-gray-700 dark:text-gray-200 line-clamp-2">{question.text}</div>
              <div class="mt-1 flex justify-between">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {new Date(question.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </span>
                {#if question.answered}
                  <span class="text-xs px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                    Answered
                  </span>
                {/if}
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
    
    <!-- Conversation Sentiment Analysis -->
    {#if $whisperStore.messages.length >= 3}
      <div>
        <h3 class="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">Conversation Overview</h3>
        <div class="bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-100 dark:border-gray-600 p-3">
          <div class="flex justify-between items-center mb-3">
            <div class="text-sm text-gray-600 dark:text-gray-300">Estimated Duration</div>
            <div class="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400">
              {Math.round($whisperStore.messages.length * 0.5)} minutes
            </div>
          </div>
          <div class="flex justify-between items-center mb-3">
            <div class="text-sm text-gray-600 dark:text-gray-300">Topic Complexity</div>
            <div class="w-24 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div class="h-full bg-blue-500" style="width: {Math.min(100, $whisperStore.messages.length * 5)}%"></div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
