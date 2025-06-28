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
  
  // Sliding window mode variables
  let viewMode = 'slide'; // Default to slide mode for better UX
  let currentSlideIndex = 0;
  let isTransitioning = false;

  // Clear question input after successful submission
  const unsubscribe = questionsStore.subscribe(state => {
    if (!state.loading && isSubmitting) {
      question = '';
      isSubmitting = false;
    }
  });
  
  // Auto-scroll questions/answers container when new answers arrive (only in scroll mode)
  afterUpdate(() => {
    if (qaContainer && autoScrollAnswers && viewMode === 'scroll') {
      qaContainer.scrollTop = 0;
    }
  });
  
  onDestroy(() => {
    unsubscribe();
  });
  
  async function handleSubmit() {
    if (!question.trim()) return;
    
    isSubmitting = true;
    dispatch('questionSubmit', { 
      question: question.trim()
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
  
  // Handle scroll events to toggle autoscroll (only in scroll mode)
  function handleScroll() {
    if (!qaContainer || viewMode === 'slide') return;
    
    const { scrollTop, scrollHeight, clientHeight } = qaContainer;
    const isAtTop = scrollTop < 30;
    autoScrollAnswers = isAtTop;
  }
  
  // Filter and prepare questions
  $: filteredQuestions = $questionsStore.questions.filter(q => {
    if (!q.text || q.text.trim() === '') return false;
    
    const lowercaseText = q.text.toLowerCase().trim();
    const hallucinations = [
      "thank you", "thank you.", "thanks.", "thanks", 
      "you're welcome", "no problem", "okay", "all right",
      "i'll keep that in mind", "that's all", "that's it"
    ];
    
    if (lowercaseText.length < 5) return false;
    return !hallucinations.includes(lowercaseText);
  }).reverse();
  
  // Sliding window navigation functions
  function goToNextSlide() {
    if (currentSlideIndex < filteredQuestions.length - 1 && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex++;
      setTimeout(() => { isTransitioning = false; }, 400);
    }
  }
  
  function goToPrevSlide() {
    if (currentSlideIndex > 0 && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex--;
      setTimeout(() => { isTransitioning = false; }, 400);
    }
  }
  
  function goToSlide(index) {
    if (index >= 0 && index < filteredQuestions.length && !isTransitioning) {
      isTransitioning = true;
      currentSlideIndex = index;
      setTimeout(() => { isTransitioning = false; }, 400);
    }
  }
  
  // Reset slide index when switching modes or when questions change
  $: if (viewMode === 'slide' && filteredQuestions.length > 0) {
    currentSlideIndex = Math.min(currentSlideIndex, filteredQuestions.length - 1);
  }
  
  // Keyboard navigation
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
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="h-full w-full max-w-7xl mx-auto bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 rounded-2xl shadow-2xl border border-slate-200/50 dark:border-gray-700/50 overflow-hidden">
  <!-- Main Grid Layout -->
  <div class="grid grid-cols-1 lg:grid-cols-3 h-full">
    
    <!-- Left Column - Input & Controls -->
    <div class="lg:col-span-1 border-r border-slate-200/50 dark:border-gray-700/50 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
      <div class="h-full flex flex-col">
        
        <!-- Header -->
        <div class="p-8 border-b border-slate-200/50 dark:border-gray-700/50">
          <div class="flex items-center space-x-4 mb-6">
            <div class="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <path d="M10 7.5h4"></path>
                <path d="M10 12h4"></path>
              </svg>
            </div>
            <div>
              <h1 class="text-2xl font-bold text-gray-900 dark:text-white">AI Assistant</h1>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Intelligent conversations</p>
            </div>
          </div>
          
          <!-- View Mode Toggle -->
          {#if filteredQuestions.length > 0}
            <div class="flex items-center space-x-1 bg-slate-100 dark:bg-gray-700 p-1.5 rounded-xl">
              <button 
                class={`flex-1 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center justify-center space-x-2 ${
                  viewMode === 'scroll' 
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-md' 
                    : 'text-gray-600 dark:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-600/50'
                }`}
                on:click={() => viewMode = 'scroll'}
                title="View all messages"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
                </svg>
                <span>All</span>
              </button>
              <button 
                class={`flex-1 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center justify-center space-x-2 ${
                  viewMode === 'slide' 
                    ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-md' 
                    : 'text-gray-600 dark:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-600/50'
                }`}
                on:click={() => viewMode = 'slide'}
                title="Focus mode"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
                <span>Focus</span>
              </button>
            </div>
          {/if}
        </div>
        
        <!-- Input Area -->
        <div class="p-8 flex-1">
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Your Question</label>
              <div class="relative">
                <textarea 
                  bind:value={question}
                  on:keydown={handleKeydown}
                  placeholder="What would you like to know? Ask about sales materials, conversations, or product features..."
                  rows="4"
                  disabled={isSubmitting}
                  class="w-full px-5 py-4 text-base text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 border border-slate-200 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 dark:focus:ring-blue-400/50 focus:border-blue-500 dark:focus:border-blue-400 resize-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 shadow-sm"
                ></textarea>
                <button 
                  class="absolute right-3 bottom-3 p-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 disabled:transform-none" 
                  disabled={!question.trim() || isSubmitting} 
                  on:click={handleSubmit}
                  title="Send message (Cmd/Ctrl + Enter)"
                  aria-label="Send message"
                >
                  {#if isSubmitting}
                    <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                  {:else}
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13"></line>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                  {/if}
                </button>
              </div>
            </div>
            
            <!-- Keyboard shortcuts -->
            <div class="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <p class="flex items-center space-x-2">
                <kbd class="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">⌘ + Enter</kbd>
                <span>Send message</span>
              </p>
              {#if viewMode === 'slide' && filteredQuestions.length > 0}
                <p class="flex items-center space-x-2">
                  <kbd class="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">← →</kbd>
                  <span>Navigate responses</span>
                </p>
              {/if}
            </div>
          </div>
        </div>
        
        <!-- Slide Navigation Controls -->
        {#if viewMode === 'slide' && filteredQuestions.length > 0}
          <div class="p-6 border-t border-slate-200/50 dark:border-gray-700/50 bg-slate-50/50 dark:bg-gray-800/50">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Navigation</h3>
              <span class="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
                {currentSlideIndex + 1} of {filteredQuestions.length}
              </span>
            </div>
            
            <div class="flex items-center space-x-3">
              <button 
                class="flex-1 p-3 rounded-lg bg-white dark:bg-gray-700 border border-slate-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center space-x-2"
                disabled={currentSlideIndex <= 0 || isTransitioning}
                on:click={goToPrevSlide}
                title="Previous message"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                <span class="text-sm font-medium">Previous</span>
              </button>
              
              <button 
                class="flex-1 p-3 rounded-lg bg-white dark:bg-gray-700 border border-slate-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md flex items-center justify-center space-x-2"
                disabled={currentSlideIndex >= filteredQuestions.length - 1 || isTransitioning}
                on:click={goToNextSlide}
                title="Next message"
              >
                <span class="text-sm font-medium">Next</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
            
            <!-- Progress dots -->
            <div class="flex justify-center space-x-2 mt-4">
              {#each filteredQuestions.slice(0, 8) as _, index}
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
              {#if filteredQuestions.length > 8}
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-2">+{filteredQuestions.length - 8}</span>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>
    
    <!-- Right Column - Content Display -->
    <div class="lg:col-span-2 flex flex-col h-full">
      
      <!-- Content Header -->
      <div class="p-6 border-b border-slate-200/50 dark:border-gray-700/50 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-200">
              {#if viewMode === 'slide' && filteredQuestions.length > 0}
                Conversation #{currentSlideIndex + 1}
              {:else if viewMode === 'scroll'}
                All Conversations
              {:else}
                Ready to Assist
              {/if}
            </h2>
          </div>
          
          {#if filteredQuestions.length > 0}
            <div class="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full">
              {filteredQuestions.length} conversation{filteredQuestions.length !== 1 ? 's' : ''}
            </div>
          {/if}
        </div>
      </div>
      
      <!-- Content Area -->
      <div class="flex-1 overflow-y-auto" bind:this={qaContainer} on:scroll={handleScroll}>
        {#if filteredQuestions.length === 0}
          <!-- Empty State -->
          <div class="h-full flex flex-col items-center justify-center text-center p-12">
            <div class="p-8 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-2xl mb-8 border border-blue-100 dark:border-blue-800/50">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400 mx-auto">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <path d="M10 7.5h4"></path>
                <path d="M10 12h4"></path>
              </svg>
            </div>
            <h3 class="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">Start a Conversation</h3>
            <p class="text-gray-600 dark:text-gray-400 max-w-md leading-relaxed text-lg">
              Ask questions about your sales materials, customer conversations, or product features. I'm here to provide intelligent insights.
            </p>
            <div class="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
              <div class="p-4 bg-white/60 dark:bg-gray-800/60 rounded-xl border border-gray-200/50 dark:border-gray-700/50">
                <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2">Sales Insights</h4>
                <p class="text-sm text-gray-600 dark:text-gray-400">Analyze sales data and customer interactions</p>
              </div>
              <div class="p-4 bg-white/60 dark:bg-gray-800/60 rounded-xl border border-gray-200/50 dark:border-gray-700/50">
                <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2">Product Knowledge</h4>
                <p class="text-sm text-gray-600 dark:text-gray-400">Get detailed information about features and specs</p>
              </div>
            </div>
          </div>
        {:else}
          {#if viewMode === 'scroll'}
            <!-- Scroll Mode - All messages -->
            <div class="p-6 space-y-8">
              {#each filteredQuestions as qa, index}
                <div class="space-y-4">
                  <!-- Question -->
                  <div class="flex items-start space-x-4">
                    <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-gray-600 to-gray-700 rounded-full flex items-center justify-center">
                      <span class="text-white text-sm font-semibold">Q</span>
                    </div>
                    <div class="flex-1 bg-gray-50 dark:bg-gray-800 rounded-2xl p-6 border border-gray-200/50 dark:border-gray-700/50">
                      <p class="text-gray-800 dark:text-gray-200 text-lg leading-relaxed">{qa.text}</p>
                      <div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
                        {formatTime(qa.timestamp)}
                      </div>
                    </div>
                  </div>
                  
                  <!-- Answer -->
                  {#if qa.loading}
                    <div class="flex items-start space-x-4">
                      <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                          <circle cx="12" cy="12" r="3"/>
                          <path d="M12 1v6m0 6v6"/>
                          <path d="m21 12-6 0m-6 0-6 0"/>
                        </svg>
                      </div>
                      <div class="flex-1 bg-white dark:bg-gray-800 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl p-8">
                        <div class="flex space-x-3 justify-center items-center">
                          <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                          <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 200ms"></div>
                          <div class="w-3 h-3 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 400ms"></div>
                        </div>
                      </div>
                    </div>
                  {:else if qa.answer}
                    <div class="flex items-start space-x-4">
                      <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                          <circle cx="12" cy="12" r="3"/>
                          <path d="M12 1v6m0 6v6"/>
                          <path d="m21 12-6 0m-6 0-6 0"/>
                        </svg>
                      </div>
                      <div class="flex-1 bg-white dark:bg-gray-800 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-lg overflow-hidden">
                        <EnhancedResponseDisplay 
                          {qa} 
                          on:followUpQuestion={(e) => dispatch('followUpQuestion', e.detail)}
                        />
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {:else if viewMode === 'slide'}
            <!-- Slide Mode - Single message focus -->
            <div class="h-full flex items-center justify-center p-8">
              <div class={`w-full max-w-5xl transition-all duration-400 ease-in-out ${isTransitioning ? 'opacity-0 transform scale-95' : 'opacity-100 transform scale-100'}`}>
                {#if filteredQuestions[currentSlideIndex]}
                  {@const qa = filteredQuestions[currentSlideIndex]}
                  <div class="space-y-8">
                    <!-- Question -->
                    <div class="bg-gradient-to-r from-slate-50 to-gray-50 dark:from-gray-800 dark:to-gray-700 rounded-2xl p-8 border border-slate-200/50 dark:border-gray-600/50 shadow-lg">
                      <div class="flex items-start space-x-6">
                        <div class="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-gray-600 to-gray-800 rounded-full flex items-center justify-center shadow-lg">
                          <span class="text-white text-lg font-bold">Q</span>
                        </div>
                        <div class="flex-1">
                          <p class="text-xl text-gray-800 dark:text-gray-200 leading-relaxed font-medium">{qa.text}</p>
                          <div class="mt-4 text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 px-3 py-1 rounded-full inline-flex items-center space-x-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <circle cx="12" cy="12" r="10"/>
                              <polyline points="12 6 12 12 16 14"/>
                            </svg>
                            <span>{formatTime(qa.timestamp)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Answer -->
                    {#if qa.loading}
                      <div class="bg-white dark:bg-gray-800 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl p-12 shadow-lg">
                        <div class="flex items-center justify-center space-x-6">
                          <div class="w-12 h-12 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
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
                          <p class="text-lg text-gray-600 dark:text-gray-400">Thinking...</p>
                        </div>
                      </div>
                    {:else if qa.answer}
                      <div class="bg-white dark:bg-gray-800 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-xl overflow-hidden">
                        <div class="p-6 border-b border-gray-100 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
                          <div class="flex items-center space-x-3">
                            <div class="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-md">
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
                                <circle cx="12" cy="12" r="3"/>
                                <path d="M12 1v6m0 6v6"/>
                                <path d="m21 12-6 0m-6 0-6 0"/>
                              </svg>
                            </div>
                            <div>
                              <h3 class="font-semibold text-gray-800 dark:text-gray-200">AI Response</h3>
                              <p class="text-sm text-gray-600 dark:text-gray-400">Powered by advanced language models</p>
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
          
          {#if viewMode === 'scroll' && !autoScrollAnswers && filteredQuestions.length > 0}
            <button 
              class="fixed bottom-8 right-8 p-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 z-10"
              aria-label="Scroll to top for newest messages"
              on:click={() => {
                autoScrollAnswers = true;
                if (qaContainer) {
                  qaContainer.scrollTop = 0;
                }
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="18 15 12 9 6 15"></polyline>
              </svg>
            </button>
          {/if}
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  /* Smooth transitions */
  .transition-all {
    transition-property: all;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  /* Custom scrollbar */
  .overflow-y-auto::-webkit-scrollbar {
    width: 8px;
  }
  
  .overflow-y-auto::-webkit-scrollbar-track {
    background: #f8fafc;
    border-radius: 4px;
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-track {
    background: #374151;
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb {
    background: #6b7280;
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
  
  :global(.dark) .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: #9ca3af;
  }
  
  /* Animation improvements */
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
      transform: translate3d(0,-1px,0);
    }
  }
  
  .animate-bounce {
    animation: bounce 1.5s infinite;
  }
</style>
