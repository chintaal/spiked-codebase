<!-- Enhanced Response Display Component for Sales AI Assistant -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { slide } from 'svelte/transition';
  
  export let qa;
  
  const dispatch = createEventDispatcher();
  
  let expandedSections = {
    starResponse: false,
    comparisonTable: false,
    relevantBullets: false,
    terminologyExplainer: false,
    analogiesOrMetaphors: false,
    customerStorySnippet: false,
    pricingInsight: false,
    followUpQuestions: false,
    longformResponse: false,
    webSearchResults: false,
    sources: false
  };
  
  function toggleSection(section) {
    expandedSections = {
      ...expandedSections,
      [section]: !expandedSections[section]
    };
  }
  
  function handleFollowUpClick(question) {
    dispatch('followUpQuestion', { question });
  }
  
  function formatTime(timestamp) {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return "";
    }
  }
  
  function getConfidenceColor(score) {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400';
    if (score >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  }
  
  function getConfidenceLabel(score) {
    if (score >= 0.8) return 'High';
    if (score >= 0.6) return 'Medium';
    return 'Low';
  }
  
  function parseStarResponse(starText) {
    if (typeof starText !== 'string') return null;
    
    const parsed = {};
    
    // Parse using regex to find each section
    const situationMatch = starText.match(/Situation:\s*([^.]*(?:\.[^ST]*)*?)(?=\s*Task:|$)/i);
    const taskMatch = starText.match(/Task:\s*([^.]*(?:\.[^SA]*)*?)(?=\s*Action:|$)/i);
    const actionMatch = starText.match(/Action:\s*([^.]*(?:\.[^SR]*)*?)(?=\s*Result:|$)/i);
    const resultMatch = starText.match(/Result:\s*([^.]*(?:\.[^S]*)*?)(?=\s*Situation:|$)/i);
    
    if (situationMatch) parsed.situation = situationMatch[1].trim();
    if (taskMatch) parsed.task = taskMatch[1].trim();
    if (actionMatch) parsed.action = actionMatch[1].trim();
    if (resultMatch) parsed.result = resultMatch[1].trim();
    
    // Only return parsed object if we found at least 2 sections
    return Object.keys(parsed).length >= 2 ? parsed : null;
  }
</script>

<div class="space-y-4">
  <!-- Question Display -->
  <div class="p-4 border border-gray-200 rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600">
    <div class="flex items-start space-x-3">
      <div class="flex items-center justify-center flex-shrink-0 w-8 h-8 text-sm font-bold text-white bg-blue-600 rounded-lg">?</div>
      <span class="font-medium leading-relaxed text-gray-800 dark:text-gray-200">{qa.text}</span>
    </div>
    <div class="mt-3 text-xs font-medium text-right text-gray-500 dark:text-gray-400">
      {formatTime(qa.timestamp)}
    </div>
  </div>

  <!-- Loading State -->
  {#if qa.loading}
    <div class="p-6 bg-white border border-gray-200 rounded-lg shadow-sm dark:bg-gray-800 dark:border-gray-600">
      <div class="flex items-center justify-center h-10 space-x-3">
        <div class="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
        <div class="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 200ms"></div>
        <div class="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 400ms"></div>
      </div>
    </div>
  {:else if qa.answer}
    <!-- Enhanced Response Display -->
    <div class="overflow-hidden bg-white border border-gray-200 rounded-lg shadow-lg dark:bg-gray-800 dark:border-gray-600">
      <!-- Header with Tags and Confidence -->
      <div class="p-5 border-b border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="flex items-center justify-center flex-shrink-0 w-8 h-8 text-sm font-bold text-white bg-green-600 rounded-lg">A</div>
            <span class="text-base font-semibold text-gray-700 dark:text-gray-300">Sales AI Response</span>
          </div>
          {#if qa.confidenceScore !== undefined}
            <div class="flex items-center space-x-3">
              <span class="text-sm text-gray-500 dark:text-gray-400">Confidence:</span>
              <div class="flex items-center space-x-2">
                <div class="w-16 h-2 overflow-hidden bg-gray-200 rounded-full dark:bg-gray-600">
                  <div class="h-full transition-all duration-300 bg-blue-500" style="width: {qa.confidenceScore * 100}%"></div>
                </div>
                <span class="text-sm font-semibold {getConfidenceColor(qa.confidenceScore)} min-w-[60px]">
                  {getConfidenceLabel(qa.confidenceScore)} ({Math.round(qa.confidenceScore * 100)}%)
                </span>
              </div>
            </div>
          {/if}
        </div>
        
        <!-- Tags Row -->
        {#if qa.intent || qa.sentiment || qa.escalationFlag}
          <div class="flex flex-wrap gap-2 mt-4">
            {#if qa.intent}
              <div class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium border border-blue-200 dark:border-blue-700">
                Intent: {qa.intent}
              </div>
            {/if}
            {#if qa.sentiment}
              <div class="px-3 py-1.5 rounded-lg text-xs font-medium border
                {qa.sentiment.toLowerCase() === 'positive' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700' : 
                 qa.sentiment.toLowerCase() === 'negative' ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700' : 
                 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-700'}">
                {qa.sentiment}
              </div>
            {/if}
            {#if qa.escalationFlag}
              <div class="px-3 py-1.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg text-xs font-medium border border-red-200 dark:border-red-700">
                ⚠️ Escalation Needed
              </div>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Main Answer -->
      <div class="p-6">
        <div class="prose dark:prose-invert max-w-none">
          <p class="mb-6 text-base leading-relaxed text-gray-700 dark:text-gray-200">{qa.answer}</p>
        </div>

        <!-- Information Gap Alert -->
        {#if qa.informationGap}
          <div class="p-4 mb-6 border-l-4 border-yellow-400 rounded-lg bg-yellow-50 dark:bg-yellow-900/30">
            <div class="flex items-start space-x-3">
              <div class="p-1 bg-yellow-400 rounded">
                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>
              </div>
              <div>
                <h4 class="text-sm font-semibold text-yellow-800 dark:text-yellow-300">Information Gap Identified</h4>
                <p class="mt-1 text-sm leading-relaxed text-yellow-700 dark:text-yellow-200">{qa.informationGap}</p>
              </div>
            </div>
          </div>
        {/if}

        <!-- Statistics Section -->
        {#if qa.statistics && qa.statistics.length > 0}
          <div class="p-5 mb-6 border border-blue-200 rounded-lg bg-blue-50 dark:bg-blue-900/30 dark:border-blue-700">
            <h4 class="flex items-center mb-4 text-sm font-bold text-blue-800 dark:text-blue-300">
              <div class="p-1.5 bg-blue-500 rounded mr-3">
                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"></path>
                </svg>
              </div>
              Key Statistics
            </h4>
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              {#each qa.statistics as stat}
                <div class="flex items-start space-x-2 text-sm text-blue-700 dark:text-blue-200">
                  <span class="mt-1 text-blue-500 dark:text-blue-400">▪</span>
                  <span class="leading-relaxed">{stat}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Sales Points Section -->
        {#if qa.salesPoints && qa.salesPoints.length > 0}
          <div class="p-5 mb-6 border border-green-200 rounded-lg bg-green-50 dark:bg-green-900/30 dark:border-green-700">
            <h4 class="flex items-center mb-4 text-sm font-bold text-green-800 dark:text-green-300">
              <div class="p-1.5 bg-green-500 rounded mr-3">
                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                </svg>
              </div>
              Sales Points
            </h4>
            <div class="grid grid-cols-1 gap-3">
              {#each qa.salesPoints as point}
                <div class="flex items-start space-x-2 text-sm text-green-700 dark:text-green-200">
                  <span class="mt-1 text-green-500 dark:text-green-400">✓</span>
                  <span class="leading-relaxed">{point}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Collapsible Enhanced Sections -->
        <div class="space-y-4">
          <!-- STAR Response -->
          {#if qa.starResponse && qa.starResponse.status === 'required'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('starResponse')}
              >
                <div class="flex items-center space-x-3">
                  <div class="p-2 bg-blue-600 rounded-lg">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                  </div>
                  <span class="font-semibold text-gray-700 dark:text-gray-300">STAR Response Framework</span>
                </div>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.starResponse ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.starResponse}
                <div class="p-6 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  {#if typeof qa.starResponse.value === 'string'}
                    <!-- Parse string format and display as structured blocks -->
                    {@const parsedStar = parseStarResponse(qa.starResponse.value)}
                    {#if parsedStar}
                      <div class="space-y-4">
                        {#if parsedStar.situation}
                          <div class="p-6 border-l-4 border-blue-500 rounded-r-lg shadow-sm bg-blue-50 dark:bg-blue-900/20">
                            <div class="flex items-center mb-4 space-x-3">
                              <div class="flex items-center justify-center w-8 h-8 bg-blue-500 rounded-full">
                                <span class="text-sm font-bold text-white">S</span>
                              </div>
                              <h4 class="text-lg font-bold text-blue-800 dark:text-blue-300">SITUATION</h4>
                            </div>
                            <div class="leading-relaxed text-blue-700 dark:text-blue-200">
                              <div class="prose dark:prose-invert max-w-none">
                                {@html parsedStar.situation.replace(/\n/g, '<br>')}
                              </div>
                            </div>
                          </div>
                        {/if}
                        
                        {#if parsedStar.task}
                          <div class="p-6 border-l-4 border-green-500 rounded-r-lg shadow-sm bg-green-50 dark:bg-green-900/20">
                            <div class="flex items-center mb-4 space-x-3">
                              <div class="flex items-center justify-center w-8 h-8 bg-green-500 rounded-full">
                                <span class="text-sm font-bold text-white">T</span>
                              </div>
                              <h4 class="text-lg font-bold text-green-800 dark:text-green-300">TASK/PROBLEM</h4>
                            </div>
                            <div class="leading-relaxed text-green-700 dark:text-green-200">
                              <div class="prose dark:prose-invert max-w-none">
                                {@html parsedStar.task.replace(/\n/g, '<br>')}
                              </div>
                            </div>
                          </div>
                        {/if}
                        
                        {#if parsedStar.action}
                          <div class="p-6 border-l-4 border-yellow-500 rounded-r-lg shadow-sm bg-yellow-50 dark:bg-yellow-900/20">
                            <div class="flex items-center mb-4 space-x-3">
                              <div class="flex items-center justify-center w-8 h-8 bg-yellow-500 rounded-full">
                                <span class="text-sm font-bold text-white">A</span>
                              </div>
                              <h4 class="text-lg font-bold text-yellow-800 dark:text-yellow-300">ACTION</h4>
                            </div>
                            <div class="leading-relaxed text-yellow-700 dark:text-yellow-200">
                              <div class="prose dark:prose-invert max-w-none">
                                {@html parsedStar.action.replace(/\n/g, '<br>')}
                              </div>
                            </div>
                          </div>
                        {/if}
                        
                        {#if parsedStar.result}
                          <div class="p-6 border-l-4 border-red-500 rounded-r-lg shadow-sm bg-red-50 dark:bg-red-900/20">
                            <div class="flex items-center mb-4 space-x-3">
                              <div class="flex items-center justify-center w-8 h-8 bg-red-500 rounded-full">
                                <span class="text-sm font-bold text-white">R</span>
                              </div>
                              <h4 class="text-lg font-bold text-red-800 dark:text-red-300">RESULT</h4>
                            </div>
                            <div class="leading-relaxed text-red-700 dark:text-red-200">
                              <div class="prose dark:prose-invert max-w-none">
                                {@html parsedStar.result.replace(/\n/g, '<br>')}
                              </div>
                            </div>
                          </div>
                        {/if}
                      </div>
                    {:else}
                      <!-- Fallback to plain text if parsing fails -->
                      <div class="text-sm leading-relaxed prose dark:prose-invert max-w-none">
                        {qa.starResponse.value}
                      </div>
                    {/if}
                  {:else if qa.starResponse.value && typeof qa.starResponse.value === 'object'}
                    <!-- Enhanced STAR display with structured blocks -->
                    <div class="space-y-4">
                      {#if qa.starResponse.value.situation}
                        <div class="p-6 border-l-4 border-blue-500 rounded-r-lg shadow-sm bg-blue-50 dark:bg-blue-900/20">
                          <div class="flex items-center mb-4 space-x-3">
                            <div class="flex items-center justify-center w-8 h-8 bg-blue-500 rounded-full">
                              <span class="text-sm font-bold text-white">S</span>
                            </div>
                            <h4 class="text-lg font-bold text-blue-800 dark:text-blue-300">SITUATION</h4>
                          </div>
                          <div class="leading-relaxed text-blue-700 dark:text-blue-200">
                            {#if qa.starResponse.value.situation.length > 300}
                              <div class="prose dark:prose-invert max-w-none">
                                {@html qa.starResponse.value.situation.replace(/\n/g, '<br>')}
                              </div>
                            {:else}
                              <p class="text-base">{qa.starResponse.value.situation}</p>
                            {/if}
                          </div>
                        </div>
                      {/if}
                      
                      {#if qa.starResponse.value.task}
                        <div class="p-6 border-l-4 border-green-500 rounded-r-lg shadow-sm bg-green-50 dark:bg-green-900/20">
                          <div class="flex items-center mb-4 space-x-3">
                            <div class="flex items-center justify-center w-8 h-8 bg-green-500 rounded-full">
                              <span class="text-sm font-bold text-white">T</span>
                            </div>
                            <h4 class="text-lg font-bold text-green-800 dark:text-green-300">TASK/PROBLEM</h4>
                          </div>
                          <div class="leading-relaxed text-green-700 dark:text-green-200">
                            {#if qa.starResponse.value.task.length > 300}
                              <div class="prose dark:prose-invert max-w-none">
                                {@html qa.starResponse.value.task.replace(/\n/g, '<br>')}
                              </div>
                            {:else}
                              <p class="text-base">{qa.starResponse.value.task}</p>
                            {/if}
                          </div>
                        </div>
                      {/if}
                      
                      {#if qa.starResponse.value.action}
                        <div class="p-6 border-l-4 border-yellow-500 rounded-r-lg shadow-sm bg-yellow-50 dark:bg-yellow-900/20">
                          <div class="flex items-center mb-4 space-x-3">
                            <div class="flex items-center justify-center w-8 h-8 bg-yellow-500 rounded-full">
                              <span class="text-sm font-bold text-white">A</span>
                            </div>
                            <h4 class="text-lg font-bold text-yellow-800 dark:text-yellow-300">ACTION</h4>
                          </div>
                          <div class="leading-relaxed text-yellow-700 dark:text-yellow-200">
                            {#if Array.isArray(qa.starResponse.value.action)}
                              <ul class="space-y-2">
                                {#each qa.starResponse.value.action as actionItem}
                                  <li class="flex items-start space-x-3">
                                    <span class="mt-1 font-bold text-yellow-500">•</span>
                                    <span class="text-base">{actionItem}</span>
                                  </li>
                                {/each}
                              </ul>
                            {:else}
                              {#if qa.starResponse.value.action.length > 300}
                                <div class="prose dark:prose-invert max-w-none">
                                  {@html qa.starResponse.value.action.replace(/\n/g, '<br>')}
                                </div>
                              {:else}
                                <p class="text-base">{qa.starResponse.value.action}</p>
                              {/if}
                            {/if}
                          </div>
                        </div>
                      {/if}
                      
                      {#if qa.starResponse.value.result}
                        <div class="p-6 border-l-4 border-red-500 rounded-r-lg shadow-sm bg-red-50 dark:bg-red-900/20">
                          <div class="flex items-center mb-4 space-x-3">
                            <div class="flex items-center justify-center w-8 h-8 bg-red-500 rounded-full">
                              <span class="text-sm font-bold text-white">R</span>
                            </div>
                            <h4 class="text-lg font-bold text-red-800 dark:text-red-300">RESULT</h4>
                          </div>
                          <div class="leading-relaxed text-red-700 dark:text-red-200">
                            {#if Array.isArray(qa.starResponse.value.result)}
                              <ul class="space-y-2">
                                {#each qa.starResponse.value.result as resultItem}
                                  <li class="flex items-start space-x-3">
                                    <span class="mt-1 text-lg text-red-500">✓</span>
                                    <span class="text-base">{resultItem}</span>
                                  </li>
                                {/each}
                              </ul>
                            {:else}
                              {#if qa.starResponse.value.result.length > 300}
                                <div class="prose dark:prose-invert max-w-none">
                                  {@html qa.starResponse.value.result.replace(/\n/g, '<br>')}
                                </div>
                              {:else}
                                <p class="text-base">{qa.starResponse.value.result}</p>
                              {/if}
                            {/if}
                          </div>
                        </div>
                      {/if}
                    </div>
                    
                    <!-- STAR Summary if available -->
                    {#if qa.starResponse.value.summary}
                      <div class="p-4 mt-6 border border-gray-200 rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600">
                        <h4 class="flex items-center mb-2 font-semibold text-gray-700 dark:text-gray-300">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2 text-gray-500">
                            <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l4 4V7l-4 4Z"></path>
                            <path d="m22 9-10 3 10 3"></path>
                          </svg>
                          Key Takeaway
                        </h4>
                        <p class="text-sm italic leading-relaxed text-gray-600 dark:text-gray-400">{qa.starResponse.value.summary}</p>
                      </div>
                    {/if}
                  {:else}
                    <!-- Fallback for other formats -->
                    <div class="text-sm leading-relaxed prose dark:prose-invert max-w-none">
                      {qa.starResponse.value}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Comparison Table -->
          {#if qa.comparisonTable && qa.comparisonTable.status === 'required'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('comparisonTable')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Comparison Table</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.comparisonTable ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.comparisonTable}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="overflow-x-auto">
                    <table class="min-w-full text-sm">
                      <thead>
                        <tr class="border-b border-gray-200 dark:border-gray-600">
                          <th class="py-2 font-medium text-left text-gray-700 dark:text-gray-300">Aspect</th>
                          <th class="py-2 font-medium text-left text-gray-700 dark:text-gray-300">tion 1</th>
                          <th class="py-2 font-medium text-left text-gray-700 dark:text-gray-300">Option 2</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each qa.comparisonTable.value as row}
                          <tr class="border-b border-gray-100 dark:border-gray-700">
                            <td class="py-2 font-medium text-gray-600 dark:text-gray-400">{row.Aspect}</td>
                            <td class="py-2 text-gray-700 dark:text-gray-300">{row['Option 1']}</td>
                            <td class="py-2 text-gray-700 dark:text-gray-300">{row['Option 2']}</td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Relevant Bullets -->
          {#if qa.relevantBullets && qa.relevantBullets.length > 0}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('relevantBullets')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Relevant Points ({qa.relevantBullets.length})</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.relevantBullets ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.relevantBullets}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <ul class="space-y-2">
                    {#each qa.relevantBullets as bullet}
                      <li class="flex items-start text-sm text-gray-700 dark:text-gray-300">
                        <span class="mt-1 mr-2 text-gray-400">•</span>
                        {bullet}
                      </li>
                    {/each}
                  </ul>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Terminology Explainer -->
          {#if qa.terminologyExplainer && qa.terminologyExplainer.status === 'required'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('terminologyExplainer')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Key Terms</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.terminologyExplainer ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.terminologyExplainer}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="space-y-3">
                    {#each qa.terminologyExplainer.value as term}
                      <div class="pl-3 border-l-4 border-blue-400">
                        <div class="font-medium text-gray-700 dark:text-gray-300">{term.term}</div>
                        <div class="mt-1 text-sm text-gray-600 dark:text-gray-400">{term.definition}</div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Analogies or Metaphors -->
          {#if qa.analogiesOrMetaphors && qa.analogiesOrMetaphors.status === 'required'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('analogiesOrMetaphors')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Analogies & Metaphors</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.analogiesOrMetaphors ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.analogiesOrMetaphors}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="text-sm italic leading-relaxed text-gray-700 dark:text-gray-300">
                    {qa.analogiesOrMetaphors.value}
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Customer Story -->
          {#if qa.customerStorySnippet && qa.customerStorySnippet.status === 'required'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('customerStorySnippet')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Customer Success Story</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.customerStorySnippet ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.customerStorySnippet}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="p-3 border-l-4 border-blue-400 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
                    <div class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                      {qa.customerStorySnippet.value}
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Pricing Insight -->
          {#if qa.pricingInsight && qa.pricingInsight.status === 'available'}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('pricingInsight')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Pricing Information</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.pricingInsight ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.pricingInsight}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="p-3 border-l-4 border-green-400 rounded-lg bg-green-50 dark:bg-green-900/20">
                    <div class="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                      {qa.pricingInsight.value}
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Long-form Response -->
          {#if qa.longformResponse}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('longformResponse')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Detailed Analysis</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.longformResponse ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.longformResponse}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="text-sm leading-relaxed prose dark:prose-invert max-w-none">
                    {qa.longformResponse}
                  </div>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Web Search Results -->
          {#if qa.webSearchResults && qa.webSearchResults.length > 0}
            <div class="overflow-hidden border border-gray-200 rounded-lg dark:border-gray-600">
              <button 
                class="flex items-center justify-between w-full px-5 py-4 text-left transition-colors bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600"
                on:click={() => toggleSection('webSearchResults')}
              >
                <span class="font-semibold text-gray-700 dark:text-gray-300">Web Research ({qa.webSearchResults.length} sources)</span>
                <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200 {expandedSections.webSearchResults ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if expandedSections.webSearchResults}
                <div class="p-5 bg-white dark:bg-gray-800" transition:slide={{ duration: 300 }}>
                  <div class="space-y-3">
                    {#each qa.webSearchResults as result}
                      <div class="p-3 border border-gray-200 rounded dark:border-gray-600">
                        <div class="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">{result.title}</div>
                        <div class="mb-2 text-xs text-gray-500 dark:text-gray-400">{result.url}</div>
                        <div class="text-sm text-gray-600 dark:text-gray-400">{result.snippet}</div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {/if}
        </div>

        <!-- Follow-up Questions -->
        {#if qa.followUpQuestions && qa.followUpQuestions.length > 0}
          <div class="p-5 mt-8 border border-blue-200 rounded-lg bg-blue-50 dark:bg-blue-900/30 dark:border-blue-700">
            <h4 class="flex items-center mb-4 text-sm font-bold text-blue-800 dark:text-blue-300">
              <div class="p-1.5 bg-blue-500 rounded mr-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M12 16v-4"></path>
                  <path d="M12 8h.01"></path>
                </svg>
              </div>
              Suggested Follow-up Questions (BANT-C)
            </h4>
            <div class="space-y-3">
              {#each qa.followUpQuestions as question}
                <button 
                  class="block w-full p-3 text-sm text-left text-blue-700 transition-colors border border-blue-200 rounded-lg dark:text-blue-300 hover:text-blue-900 dark:hover:text-blue-100 hover:bg-blue-100 dark:hover:bg-blue-800/50 dark:border-blue-700 hover:border-blue-300 dark:hover:border-blue-600"
                  on:click={() => handleFollowUpClick(question)}
                >
                  → {question}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Sources - Always Visible NotebookLM Style -->
        {#if qa.sources && qa.sources.length > 0}
          <div class="p-6 mt-8 border shadow-sm bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-800 dark:to-gray-700 rounded-xl border-slate-200 dark:border-gray-600">
            <!-- Sources Header -->
            <div class="flex items-center mb-6 space-x-3">
              <div class="p-2.5 bg-indigo-600 rounded-xl shadow-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14,2 14,8 20,8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10,9 9,9 8,9"></polyline>
                </svg>
              </div>
              <div>
                <h3 class="text-lg font-bold text-gray-800 dark:text-gray-200">Sources</h3>
                <p class="text-sm text-gray-600 dark:text-gray-400">Information verified from {qa.sources.length} source{qa.sources.length !== 1 ? 's' : ''}</p>
              </div>
            </div>

            <!-- Sources Grid -->
            <div class="grid grid-cols-1 gap-4 mb-6 md:grid-cols-2">
              {#each qa.sources as source, i}
                  {@const sourceStr = typeof source === 'string' ? source : JSON.stringify(source)}
                  <div class="group relative bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-600 rounded-xl p-4 hover:shadow-lg hover:border-indigo-300 dark:hover:border-indigo-500 transition-all duration-300 hover:scale-[1.02]">
                    <!-- Source Number Badge -->
                    <div class="absolute flex items-center justify-center text-xs font-bold text-white rounded-full shadow-lg -top-2 -left-2 w-7 h-7 bg-gradient-to-br from-indigo-600 to-purple-600">
                      {i + 1}
                    </div>
                    
                    <!-- Source Content -->
                    <div class="ml-3">
                      <!-- Source Type Icon and Title -->
                      <div class="flex items-start mb-3 space-x-3">
                        <div class="flex-shrink-0 mt-0.5">
                          {#if typeof source === 'string' && source.toLowerCase().includes('.pdf')}
                          <div class="flex items-center justify-center w-10 h-10 bg-red-100 shadow-sm dark:bg-red-900/30 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-red-600 dark:text-red-400">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                              <polyline points="14,2 14,8 20,8"></polyline>
                              <line x1="16" y1="13" x2="8" y2="13"></line>
                              <line x1="16" y1="17" x2="8" y2="17"></line>
                              <polyline points="10,9 9,9 8,9"></polyline>
                            </svg>
                          </div>
                        {:else if typeof source === 'string' && (source.toLowerCase().includes('.docx') || source.toLowerCase().includes('.doc'))}
                          <div class="flex items-center justify-center w-10 h-10 bg-blue-100 shadow-sm dark:bg-blue-900/30 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                              <polyline points="14,2 14,8 20,8"></polyline>
                              <line x1="16" y1="13" x2="8" y2="13"></line>
                              <line x1="16" y1="17" x2="8" y2="17"></line>
                            </svg>
                          </div>
                        {:else if typeof source === 'string' && (source.toLowerCase().includes('.pptx') || source.toLowerCase().includes('.ppt'))}
                          <div class="flex items-center justify-center w-10 h-10 bg-orange-100 shadow-sm dark:bg-orange-900/30 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-orange-600 dark:text-orange-400">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                              <polyline points="14,2 14,8 20,8"></polyline>
                              <rect x="8" y="10" width="8" height="6" rx="1"></rect>
                            </svg>
                          </div>
                        {:else if typeof source === 'string' && source.toLowerCase().includes('http')}
                          <div class="flex items-center justify-center w-10 h-10 bg-green-100 shadow-sm dark:bg-green-900/30 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600 dark:text-green-400">
                              <circle cx="12" cy="12" r="10"></circle>
                              <path d="M12 16l4-4-4-4M8 12h8"></path>
                            </svg>
                          </div>
                        {:else}
                          <div class="flex items-center justify-center w-10 h-10 bg-gray-100 shadow-sm dark:bg-gray-600 rounded-xl">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-600 dark:text-gray-400">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                              <polyline points="14,2 14,8 20,8"></polyline>
                            </svg>
                          </div>
                        {/if}
                      </div>
                      <div class="flex-1 min-w-0">
                        <h5 class="mb-1 text-sm font-bold leading-tight text-gray-800 truncate transition-colors dark:text-gray-200 group-hover:text-indigo-700 dark:group-hover:text-indigo-300">
                          {sourceStr.split('/').pop()?.replace(/\.[^/.]+$/, "") || sourceStr}
                        </h5>
                        <p class="text-xs leading-relaxed text-gray-500 truncate dark:text-gray-400">
                          {sourceStr}
                        </p>
                      </div>
                    </div>
                    
                    <!-- Source Metadata -->
                    <div class="flex items-center justify-between text-xs">
                      <div class="flex items-center space-x-3 text-gray-400 dark:text-gray-500">
                        <div class="flex items-center space-x-1">
                          <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                          <span>Verified</span>
                        </div>
                        <div class="flex items-center space-x-1">
                          <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M9 11H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h4l4 4V7l-4 4Z"></path>
                            <path d="m22 9-10 3 10 3"></path>
                          </svg>
                          <span>Referenced</span>
                        </div>
                      </div>
                      <!-- View Button -->
                      <button class="px-2 py-1 text-xs font-medium text-indigo-700 transition-all duration-200 bg-indigo-100 rounded-lg opacity-0 group-hover:opacity-100 dark:bg-indigo-900/50 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/70">
                        View
                      </button>
                    </div>
                  </div>
                </div>
              {/each}
            </div>

            <!-- Sources Summary Footer -->
            <div class="pt-4 border-t border-slate-200 dark:border-gray-600">
              <div class="flex items-center justify-between text-sm">
                <div class="flex items-center space-x-2 text-gray-700 dark:text-gray-300">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600">
                    <path d="M20 6L9 17l-5-5"></path>
                  </svg>
                  <span class="font-medium">All sources verified and current</span>
                </div>
                <div class="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                  <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span>Last updated: {formatTime(qa.timestamp)}</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
