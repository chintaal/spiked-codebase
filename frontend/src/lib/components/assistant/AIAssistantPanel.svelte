<script>
  import { onDestroy, createEventDispatcher, afterUpdate } from 'svelte';
  import { questionsStore, currentQuestion } from '$lib/stores/questions.js';
  import { darkMode } from '$lib/stores/ui.js';
  import EnhancedResponseDisplay from './EnhancedResponseDisplay_new.svelte';
  
  const dispatch = createEventDispatcher();
  
  let question = '';
  let isSubmitting = false;
  let qaContainer;
  let autoScrollAnswers = true;
  let responseLength = 500; // Default response length
  
  // Enhanced view modes
  let viewMode = 'scroll'; // 'scroll', 'slide', or 'topScroll'
  let currentSlideIndex = 0;
  let isTransitioning = false;
  let showViewModeOptions = false;

  // Format response length for display
  $: responseLengthDisplay = responseLength < 1000 ? responseLength : `${(responseLength/1000).toFixed(1)}k`;
  
  // Clear question input after successful submission
  const unsubscribe = questionsStore.subscribe(state => {
    if (!state.loading && isSubmitting) {
      question = '';
      isSubmitting = false;
    }
  });
  
  // Auto-scroll questions/answers container based on mode
  afterUpdate(() => {
    if (qaContainer && autoScrollAnswers) {
      if (viewMode === 'scroll') {
        qaContainer.scrollTop = 0; // Scroll to top for newest
      } else if (viewMode === 'topScroll') {
        qaContainer.scrollTop = qaContainer.scrollHeight; // Scroll to bottom for oldest first
      }
    }
  });
  
  onDestroy(() => {
    unsubscribe();
  });
  
  async function handleSubmit() {
    // Don't submit empty or whitespace-only questions
    if (!question.trim()) return;
    
    isSubmitting = true;
    dispatch('questionSubmit', { 
      question: question.trim(),
      responseLength: responseLength // Pass response length to parent
    });
  }
  
  function formatTime(timestamp) {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return "";
    }
  }
  
  // Handle scroll events based on mode
  function handleScroll() {
    if (!qaContainer || viewMode === 'slide') return;
    
    const { scrollTop, scrollHeight, clientHeight } = qaContainer;
    
    if (viewMode === 'scroll') {
      // In newest-first mode, consider near-top scrolls as top
      const isAtTop = scrollTop < 30;
      autoScrollAnswers = isAtTop;
    } else if (viewMode === 'topScroll') {
      // In oldest-first mode, consider near-bottom scrolls as bottom
      const isAtBottom = scrollTop > scrollHeight - clientHeight - 30;
      autoScrollAnswers = isAtBottom;
    }
  }
  
  // Filter and prepare questions based on view mode
  $: filteredQuestions = (() => {
    const questions = $questionsStore.questions.filter(q => {
      if (!q.text || q.text.trim() === '') return false;
      
      const lowercaseText = q.text.toLowerCase().trim();
      const hallucinations = [
        "thank you", "thank you.", "thanks.", "thanks", 
        "you're welcome", "no problem", "okay", "all right",
        "i'll keep that in mind", "that's all", "that's it"
      ];
      
      if (lowercaseText.length < 5) return false;
      return !hallucinations.includes(lowercaseText);
    });
    
    // Return in correct order based on view mode
    return viewMode === 'topScroll' ? questions : questions.reverse();
  })();
  
  // Sliding window navigation functions
  function goToNextSlide() {
    if (currentSlideIndex < filteredQuestions.length - 1 && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex++;
      setTimeout(() => { isTransitioning = false; }, 300);
    }
  }
  
  function goToPrevSlide() {
    if (currentSlideIndex > 0 && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex--;
      setTimeout(() => { isTransitioning = false; }, 300);
    }
  }
  
  function goToSlide(index) {
    if (index >= 0 && index < filteredQuestions.length && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex = index;
      setTimeout(() => { isTransitioning = false; }, 300);
    }
  }
  
  // Reset slide index when switching modes or when questions change
  $: if (viewMode === 'slide' && filteredQuestions.length > 0) {
    currentSlideIndex = Math.min(currentSlideIndex, filteredQuestions.length - 1);
  }
  
  // Keyboard navigation for slide mode
  function handleKeydown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSubmit();
    } else if (viewMode === 'slide' && filteredQuestions.length > 0) {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        goToPrevSlide();
      } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        goToNextSlide();
      }
    }
  }
  
  let viewModeButton;
  
  // Calculate dropdown position
  function getDropdownPosition() {
    if (!viewModeButton) return { top: 0, right: 0 };
    
    const rect = viewModeButton.getBoundingClientRect();
    return {
      top: rect.bottom + 8,
      right: window.innerWidth - rect.right
    };
  }
  
  $: dropdownPosition = showViewModeOptions ? getDropdownPosition() : { top: 0, right: 0 };
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- Portal dropdown to body level -->
{#if showViewModeOptions}
  <div 
    class="dropdown-portal fixed bg-white/95 dark:bg-gray-800/95 backdrop-blur-md rounded-xl shadow-2xl border border-slate-200/50 dark:border-gray-600/50 py-2 min-w-[180px] transform-gpu transition-all duration-200 ease-out origin-top-right scale-100 opacity-100"
    style="top: {dropdownPosition.top}px; right: {dropdownPosition.right}px; z-index: 999999;"
    on:mouseenter={() => showViewModeOptions = true}
    on:mouseleave={() => showViewModeOptions = false}
  >
    <button 
      class={`w-full px-4 py-3 text-left text-sm hover:bg-slate-50 dark:hover:bg-gray-700/50 flex items-center space-x-3 transition-colors ${
        viewMode === 'scroll' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
      }`}
      on:click={() => { viewMode = 'scroll'; showViewModeOptions = false; }}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
      </svg>
      <div>
        <div class="font-medium">Newest First</div>
        <div class="text-xs opacity-75">Latest messages at top</div>
      </div>
    </button>
    <button 
      class={`w-full px-4 py-3 text-left text-sm hover:bg-slate-50 dark:hover:bg-gray-700/50 flex items-center space-x-3 transition-colors ${
        viewMode === 'topScroll' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
      }`}
      on:click={() => { viewMode = 'topScroll'; showViewModeOptions = false; }}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 5v14m-7-7l7-7 7 7"/>
      </svg>
      <div>
        <div class="font-medium">Oldest First</div>
        <div class="text-xs opacity-75">Chronological order</div>
      </div>
    </button>
    <button 
      class={`w-full px-4 py-3 text-left text-sm hover:bg-slate-50 dark:hover:bg-gray-700/50 flex items-center space-x-3 transition-colors ${
        viewMode === 'slide' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
      }`}
      on:click={() => { viewMode = 'slide'; showViewModeOptions = false; }}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="9" cy="9" r="2"/>
        <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
      </svg>
      <div>
        <div class="font-medium">Focus Mode</div>
        <div class="text-xs opacity-75">One conversation at a time</div>
      </div>
    </button>
  </div>
{/if}

<div class="h-full flex flex-col bg-gradient-to-br from-slate-50 to-blue-50/30 dark:from-gray-900 dark:to-gray-800 rounded-xl shadow-xl border border-slate-200/60 dark:border-gray-700/60">
  <!-- Enhanced Header -->
  <div class="px-6 py-4 border-b border-slate-200/60 dark:border-gray-700/60 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-t-xl">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg shadow-md">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            <path d="M10 7.5h4"></path>
            <path d="M10 12h4"></path>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white">AI Assistant</h2>
          <p class="text-xs text-gray-500 dark:text-gray-400">Intelligent conversations</p>
        </div>
      </div>
      
      <!-- Enhanced View Mode Toggle with Hover Options -->
      {#if filteredQuestions.length > 0}
        <div class="relative">
          <button 
            bind:this={viewModeButton}
            class="p-2.5 rounded-xl bg-slate-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-slate-200 dark:hover:bg-gray-600 transition-all duration-200 shadow-sm hover:shadow-md"
            on:mouseenter={() => showViewModeOptions = true}
            on:mouseleave={() => showViewModeOptions = false}
            title="View modes"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
            </svg>
          </button>
        </div>
      {/if}
    </div>
  </div>
  
  <!-- Enhanced Input Area -->
  <div class="px-6 py-4 bg-white/50 dark:bg-gray-800/50 border-b border-slate-200/40 dark:border-gray-700/40 relative z-10">
    <div class="relative z-10">
      <textarea 
        bind:value={question}
        on:keydown={handleKeydown}
        placeholder="What would you like to know? Ask about sales materials, conversations, or product features..."
        rows="3"
        disabled={isSubmitting}
        class="w-full px-5 py-4 pr-14 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 dark:focus:ring-blue-400/50 focus:border-blue-500/50 dark:focus:border-blue-400/50 resize-none border border-slate-200 dark:border-gray-600 transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 shadow-sm text-base leading-relaxed relative z-10"
      ></textarea>
      <button 
        class="absolute right-3 bottom-3 p-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 disabled:transform-none z-20" 
        disabled={!question.trim() || isSubmitting} 
        on:click={handleSubmit}
        title="Send message (Cmd/Ctrl + Enter)"
        aria-label="Send message"
      >
        {#if isSubmitting}
          <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 11-6.219-8.56"/>
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        {/if}
      </button>
    </div>
    <div class="mt-3 text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-4">
      <span class="flex items-center space-x-1">
        <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">⌘ Enter</kbd>
        <span>to send</span>
      </span>
      {#if viewMode === 'slide' && filteredQuestions.length > 0}
        <span class="flex items-center space-x-1">
          <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">← →</kbd>
          <span>to navigate</span>
        </span>
      {/if}
    </div>
  </div>
  
  <!-- Enhanced Slide Mode Navigation -->
  {#if viewMode === 'slide' && filteredQuestions.length > 0}
    <div class="px-6 py-3 bg-slate-50/50 dark:bg-gray-800/50 border-b border-slate-200/40 dark:border-gray-700/40 flex items-center justify-between">
      <button 
        class="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white dark:bg-gray-700 border border-slate-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-slate-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
        disabled={currentSlideIndex <= 0 || isTransitioning}
        on:click={goToPrevSlide}
        title="Previous message"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        <span class="text-sm font-medium">Previous</span>
      </button>
      
      <div class="flex items-center space-x-3">
        <span class="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-700 px-3 py-1 rounded-full border border-slate-200 dark:border-gray-600">
          {currentSlideIndex + 1} of {filteredQuestions.length}
        </span>
        <div class="flex space-x-1">
          {#each filteredQuestions.slice(0, 6) as _, index}
            <button 
              class={`w-2 h-2 rounded-full transition-all duration-200 ${
                index === currentSlideIndex 
                  ? 'bg-blue-600 dark:bg-blue-400 w-6' 
                  : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500'
              }`}
              on:click={() => goToSlide(index)}
              title={`Go to message ${index + 1}`}
            ></button>
          {/each}
          {#if filteredQuestions.length > 6}
            <span class="text-xs text-gray-400 ml-2">+{filteredQuestions.length - 6}</span>
          {/if}
        </div>
      </div>
      
      <button 
        class="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white dark:bg-gray-700 border border-slate-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-slate-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
        disabled={currentSlideIndex >= filteredQuestions.length - 1 || isTransitioning}
        on:click={goToNextSlide}
        title="Next message"
      >
        <span class="text-sm font-medium">Next</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>
  {/if}
  
  <!-- Enhanced Main Content Area -->
  <div class="flex-1 min-h-0 relative">
    <div class="absolute inset-0 overflow-y-auto scroll-smooth" bind:this={qaContainer} on:scroll={handleScroll}>
      {#if filteredQuestions.length === 0}
        <!-- Enhanced Empty State -->
        <div class="h-full flex flex-col items-center justify-center text-center p-8">
          <div class="p-8 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl mb-8 border border-blue-100 dark:border-blue-800/50 shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400 mx-auto">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              <path d="M10 7.5h4"></path>
              <path d="M10 12h4"></path>
            </svg>
          </div>
          <h3 class="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">Ready to Assist</h3>
          <p class="text-gray-600 dark:text-gray-400 max-w-lg leading-relaxed text-lg mb-8">
            Ask questions about your sales materials, customer conversations, or product features. I'm here to provide intelligent insights and answers.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl">
            <div class="p-4 bg-white/70 dark:bg-gray-800/70 rounded-xl border border-slate-200/50 dark:border-gray-700/50 backdrop-blur-sm">
              <div class="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center mb-3 mx-auto">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600 dark:text-green-400">
                  <path d="M9 11l3 3L22 4"/>
                  <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.7 0 3.29.47 4.65 1.29"/>
                </svg>
              </div>
              <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2 text-sm">Sales Analysis</h4>
              <p class="text-xs text-gray-600 dark:text-gray-400">Deep insights into sales data and performance</p>
            </div>
            <div class="p-4 bg-white/70 dark:bg-gray-800/70 rounded-xl border border-slate-200/50 dark:border-gray-700/50 backdrop-blur-sm">
              <div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mb-3 mx-auto">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
                  <path d="M12 20h9"/>
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
                </svg>
              </div>
              <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2 text-sm">Content Review</h4>
              <p class="text-xs text-gray-600 dark:text-gray-400">Analyze and summarize sales materials</p>
            </div>
            <div class="p-4 bg-white/70 dark:bg-gray-800/70 rounded-xl border border-slate-200/50 dark:border-gray-700/50 backdrop-blur-sm">
              <div class="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mb-3 mx-auto">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-600 dark:text-purple-400">
                  <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.582a.5.5 0 0 1 0 .962L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>
                </svg>
              </div>
              <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2 text-sm">Smart Insights</h4>
              <p class="text-xs text-gray-600 dark:text-gray-400">AI-powered recommendations and tips</p>
            </div>
          </div>
        </div>
      {:else}
        {#if viewMode === 'scroll' || viewMode === 'topScroll'}
          <!-- Enhanced Scroll Modes -->
          <div class="p-6 space-y-6 pb-20">
            {#each filteredQuestions as qa, index}
              <div class="space-y-4 group">
                <!-- Enhanced Question Card -->
                <div class="bg-gradient-to-r from-slate-50 to-gray-50 dark:from-gray-800 dark:to-gray-700 rounded-xl p-5 border border-slate-200/60 dark:border-gray-600/60 shadow-sm hover:shadow-md transition-all duration-200">
                  <div class="flex items-start space-x-4">
                    <div class="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-gray-600 to-gray-700 rounded-full flex items-center justify-center shadow-md">
                      <span class="text-white text-sm font-semibold">Q</span>
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-gray-800 dark:text-gray-200 leading-relaxed font-medium">{qa.text}</p>
                      <div class="mt-3 flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400">
                        <span class="flex items-center space-x-1">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                            <polyline points="12 6 12 12 16 14"/>
                          </svg>
                          <span>{formatTime(qa.timestamp)}</span>
                        </span>
                        <span class="bg-gray-200 dark:bg-gray-600 px-2 py-0.5 rounded-full">#{index + 1}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Enhanced Answer -->
                {#if qa.loading}
                  <div class="bg-white dark:bg-gray-800 border border-slate-200/60 dark:border-gray-700/60 rounded-xl p-8 shadow-lg">
                    <div class="flex items-center justify-center space-x-6">
                      <div class="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-md">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                          <circle cx="12" cy="12" r="3"/>
                          <path d="M12 1v6m0 6v6"/>
                          <path d="m21 12-6 0m-6 0-6 0"/>
                        </svg>
                      </div>
                      <div class="flex space-x-2">
                        <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                        <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 200ms"></div>
                        <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 400ms"></div>
                      </div>
                      <p class="text-lg text-gray-600 dark:text-gray-400 font-medium">Thinking...</p>
                    </div>
                  </div>
                {:else if qa.answer}
                  <div class="bg-white dark:bg-gray-800 border border-slate-200/60 dark:border-gray-700/60 rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-200">
                    <div class="p-4 border-b border-slate-100 dark:border-gray-700 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 dark:from-blue-900/10 dark:to-indigo-900/10">
                      <div class="flex items-center space-x-3">
                        <div class="w-7 h-7 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-md">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                            <circle cx="12" cy="12" r="3"/>
                            <path d="M12 1v6m0 6v6"/>
                            <path d="m21 12-6 0m-6 0-6 0"/>
                          </svg>
                        </div>
                        <div>
                          <h4 class="font-semibold text-gray-800 dark:text-gray-200">AI Response</h4>
                          <p class="text-xs text-gray-600 dark:text-gray-400">Powered by advanced language models</p>
                        </div>
                      </div>
                    </div>
                    <EnhancedResponseDisplay 
                      {qa} 
                      on:followUpQuestion={(e) => dispatch('followUpQuestion', e.detail)}
                    />
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else if viewMode === 'slide'}
          <!-- Enhanced Slide Mode -->
          <div class="min-h-full flex items-center justify-center p-8">
            <div class={`w-full max-w-5xl transition-all duration-400 ease-out ${isTransitioning ? 'opacity-0 transform scale-95' : 'opacity-100 transform scale-100'}`}>
              {#if filteredQuestions[currentSlideIndex]}
                {@const qa = filteredQuestions[currentSlideIndex]}
                <div class="space-y-6">
                  <!-- Enhanced Focused Question -->
                  <div class="bg-gradient-to-br from-slate-50 to-blue-50 dark:from-gray-800 dark:to-gray-700 rounded-2xl p-8 border border-slate-200/60 dark:border-gray-600/60 shadow-xl">
                    <div class="flex items-start space-x-6">
                      <div class="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-gray-600 to-gray-800 rounded-full flex items-center justify-center shadow-lg">
                        <span class="text-white text-lg font-bold">Q</span>
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="text-xl text-gray-800 dark:text-gray-200 leading-relaxed font-medium mb-4">{qa.text}</p>
                        <div class="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                          <span class="flex items-center space-x-2 bg-white/60 dark:bg-gray-700/60 px-3 py-1 rounded-full">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <circle cx="12" cy="12" r="10"/>
                              <polyline points="12 6 12 12 16 14"/>
                            </svg>
                            <span>{formatTime(qa.timestamp)}</span>
                          </span>
                          <span class="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-3 py-1 rounded-full font-medium">
                            #{currentSlideIndex + 1} of {filteredQuestions.length}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Enhanced Focused Answer -->
                  {#if qa.loading}
                    <div class="bg-white dark:bg-gray-800 border border-slate-200/60 dark:border-gray-700/60 rounded-2xl p-12 shadow-xl">
                      <div class="flex items-center justify-center space-x-8">
                        <div class="w-14 h-14 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
                          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                            <circle cx="12" cy="12" r="3"/>
                            <path d="M12 1v6m0 6v6"/>
                            <path d="m21 12-6 0m-6 0-6 0"/>
                          </svg>
                        </div>
                        <div class="flex space-x-3">
                          <div class="w-4 h-4 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                          <div class="w-4 h-4 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 200ms"></div>
                          <div class="w-4 h-4 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 400ms"></div>
                        </div>
                        <p class="text-xl text-gray-600 dark:text-gray-400 font-medium">Analyzing your question...</p>
                      </div>
                    </div>
                  {:else if qa.answer}
                    <div class="bg-white dark:bg-gray-800 border border-slate-200/60 dark:border-gray-700/60 rounded-2xl shadow-2xl overflow-hidden">
                      <div class="p-6 border-b border-slate-100 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
                        <div class="flex items-center space-x-4">
                          <div class="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                              <circle cx="12" cy="12" r="3"/>
                              <path d="M12 1v6m0 6v6"/>
                              <path d="m21 12-6 0m-6 0-6 0"/>
                            </svg>
                          </div>
                          <div>
                            <h3 class="text-lg font-bold text-gray-800 dark:text-gray-200">AI Response</h3>
                            <p class="text-sm text-gray-600 dark:text-gray-400">Intelligent analysis and insights</p>
                          </div>
                        </div>
                      </div>
                      <EnhancedResponseDisplay 
                        {qa} 
                        on:followUpQuestion={(e) => dispatch('followUpQuestion', e.detail)}
                      />
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          </div>
        {/if}
        
        <!-- Enhanced Scroll Indicator -->
        {#if (viewMode === 'scroll' || viewMode === 'topScroll') && !autoScrollAnswers && filteredQuestions.length > 0}
          <button 
            class="fixed bottom-6 right-6 p-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl hover:shadow-2xl transition-all duration-200 z-10 transform hover:scale-110"
            aria-label={viewMode === 'scroll' ? 'Scroll to top for newest' : 'Scroll to bottom for newest'}
            on:click={() => {
              autoScrollAnswers = true;
              if (qaContainer) {
                qaContainer.scrollTo({
                  top: viewMode === 'scroll' ? 0 : qaContainer.scrollHeight,
                  behavior: 'smooth'
                });
              }
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              {#if viewMode === 'scroll'}
                <polyline points="18 15 12 9 6 15"></polyline>
              {:else}
                <polyline points="6 9 12 15 18 9"></polyline>
              {/if}
            </svg>
          </button>
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  /* Portal dropdown styling */
  :global(.dropdown-portal) {
    z-index: 999999 !important;
    position: fixed !important;
    pointer-events: auto !important;
  }

  /* Reset any conflicting z-index rules */
  :global(textarea), :global(input) {
    z-index: auto !important;
  }

  :global(button) {
    z-index: auto !important;
  }

  /* Enhanced scrollbar */
  .overflow-y-auto::-webkit-scrollbar {
    width: 8px;
  }
  
  .overflow-y-auto::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 10px;
    margin: 4px;
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb {
    background: linear-gradient(to bottom, #cbd5e1, #94a3b8);
    border-radius: 10px;
    border: 2px solid transparent;
    background-clip: padding-box;
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb {
    background: linear-gradient(to bottom, #4b5563, #6b7280);
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(to bottom, #94a3b8, #64748b);
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(to bottom, #6b7280, #9ca3af);
  }
  
  /* Smooth scroll behavior */
  .scroll-smooth {
    scroll-behavior: smooth;
  }
  
  /* Enhanced animations */
  @keyframes bounce {
    0%, 20%, 53%, 80%, 100% {
      animation-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
      transform: translate3d(0,0,0);
    }
    40%, 43% {
      animation-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
      transform: translate3d(0, -8px, 0);
    }
    70% {
      animation-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
      transform: translate3d(0, -4px, 0);
    }
    90% {
      transform: translate3d(0,-2px,0);
    }
  }
</style>