<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { darkMode } from '$lib/stores/ui.js';
  import { questionsStore } from '$lib/stores/questions.js';
  import { transcriptionStore } from '$lib/stores/transcription.js';
  import { currentLayoutConfig, componentWidths, layoutActions } from '$lib/stores/layouts.js';
  import ConversationPanel from '$lib/components/conversation/ConversationPanel.svelte';
  import MeetingPanel from '$lib/components/meeting/MeetingPanel.svelte';
  import AIAssistantPanel from '$lib/components/assistant/AIAssistantPanel.svelte';
  import AnalyticsPanel from '$lib/components/analytics/AnalyticsPanel.svelte';
  import LayoutSelector from '$lib/components/layout/LayoutSelector.svelte';
  import ComponentToggle from '$lib/components/layout/ComponentToggle.svelte';
  import QuickLayouts from '$lib/components/layout/QuickLayouts.svelte';
  
  // Mode toggle state
  let currentMode = 'microphone'; // 'microphone' or 'meeting'
  
  // Resizable columns state
  let containerEl;
  let isDragging = false;
  let activeHandle = null;
  let startX = 0;
  let startWidths = {};
  
  // Panel controls state
  let showPanelControls = false;
  
  // Component widths from layout store
  $: conversationWidth = $componentWidths.conversation;
  $: assistantWidth = $componentWidths.assistant;
  $: analyticsWidth = $componentWidths.analytics;
  
  // Check which components are enabled
  $: conversationEnabled = $currentLayoutConfig?.components?.conversation?.enabled ?? true;
  $: assistantEnabled = $currentLayoutConfig?.components?.assistant?.enabled ?? true;
  $: analyticsEnabled = $currentLayoutConfig?.components?.analytics?.enabled ?? true;
  
  // Calculate enabled panels count for resize handles
  $: enabledPanels = [conversationEnabled, assistantEnabled, analyticsEnabled].filter(Boolean).length;
  
  // Function to handle search submissions
  async function handleQuestionSubmit(event) {
    const question = event.detail.question;
    const responseLength = event.detail.responseLength || 500;
    submitQuestion(question, responseLength);
  }
  
  // Enhanced RAG-based Analyze API integration
  async function submitQuestion(question, responseLength = 500) {
    try {
      // Show loading state in the AI Assistant panel
      questionsStore.addQuestion(question, true);
      
      try {
        // Call the enhanced analyze API with RAG and gap detection
        const response = await fetch('http://localhost:8000/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            conversation: question,
            max_response_length: responseLength,
            tone: 'professional',
            include_sources: true,
            include_web_search: true,
            detect_gaps: true // Enable information gap detection
          }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch answer');
        }
        
        const data = await response.json();
        console.log("Enhanced RAG response:", data);
        
        // Display information gaps if detected
        if (data.information_gaps && data.information_gaps.length > 0) {
          const gapSummary = `Information gaps detected: ${data.information_gaps.map(gap => gap.category || gap.type).join(', ')}`;
          transcriptionStore.addSystemMessage(gapSummary);
          
          // Add detailed gap information
          data.information_gaps.forEach((gap, index) => {
            const gapDetail = `Gap ${index + 1}: ${gap.description || gap.question || gap.missing_info}`;
            transcriptionStore.addSystemMessage(gapDetail);
          });
        }
        
        questionsStore.updateEnhancedAnswer(question, data);
      } catch (error) {
        console.error('Error analyzing:', error);
        questionsStore.updateAnswer(question, `Error: ${error.message}. Please try again.`);
      }
    } catch (error) {
      console.error('Error processing question:', error);
      questionsStore.updateAnswer(question, 'Error retrieving answer. Please try again.');
    }
  }
  
  // Function to handle transcription message clicks
  function handleConversationMessageClick(event) {
    const messageText = event.detail.text;
    submitQuestion(messageText);
  }
  
  // Function to handle layout changes
  function handleLayoutChanged(event) {
    const { layoutId } = event.detail;
    console.log('Layout changed to:', layoutId);
  }
  
  // Function to handle drag-and-drop from conversation
  function handleConversationDrop(event) {
    const messageText = event.detail.text;
    submitQuestion(messageText);
  }
  
  // Function to handle component toggles
  // Function to handle component toggles
  function handleComponentToggled(event) {
    const { componentName } = event.detail;
    console.log('Component toggled:', componentName);
  }
  
  // Function to toggle panel controls
  function togglePanelControls() {
    showPanelControls = !showPanelControls;
  }
  
  // Automatic question detection from conversation
  function handleQuestionDetected(event) {
    const detectedQuestion = event.detail.question;
    console.log('Question detected:', detectedQuestion);
    submitQuestion(detectedQuestion);
  }
  
  // Function to handle follow-up questions
  function handleFollowUpQuestion(event) {
    const question = event.detail.question;
    console.log('Follow-up question clicked:', question);
    submitQuestion(question);
  }
  
  // Handle the sendToAssistant event from auto-accumulation
  function handleSendToAssistant(event) {
    const question = event.detail.question;
    const isAutoSent = event.detail.autoSent;
    console.log('Auto-sending accumulated transcription:', question);
    if (question && question.trim()) {
      submitQuestion(question);
      // Show user feedback that transcription was sent with gap detection
      const wordCount = question.trim().split(/\s+/).length;
      transcriptionStore.addSystemMessage(`Analyzing ${wordCount} words for content and information gaps...`);
    }
  }
  
  // Function to handle meeting-to-assistant communication
  function handleMeetingToAssistant(event) {
    const question = event.detail.question;
    const context = event.detail.context || '';
    console.log('Sending meeting content to assistant:', question);
    submitQuestion(question);
  }
  
  // Function to toggle between modes
  function toggleMode(mode) {
    currentMode = mode;
    // Clear any active states when switching modes
    if (mode === 'microphone') {
      // Could add cleanup for meeting mode if needed
    } else if (mode === 'meeting') {
      // Could add cleanup for microphone mode if needed
    }
  }
  
  // Resize functionality
  function startResize(event, handleType) {
    event.preventDefault();
    isDragging = true;
    activeHandle = handleType;
    startX = event.clientX;
    startWidths = {
      conversation: conversationWidth,
      assistant: assistantWidth,
      analytics: analyticsWidth
    };
    
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }
  
  function handleResize(event) {
    if (!isDragging || !containerEl) return;
    
    const containerRect = containerEl.getBoundingClientRect();
    const deltaX = event.clientX - startX;
    const deltaPercent = (deltaX / containerRect.width) * 100;
    
    if (activeHandle === 'conversation-assistant') {
      // Resizing between conversation and assistant panels
      const newConversationWidth = Math.max(15, Math.min(50, startWidths.conversation + deltaPercent));
      const newAssistantWidth = Math.max(30, Math.min(70, startWidths.assistant - deltaPercent));
      
      // Ensure total doesn't exceed available space
      const totalUsed = newConversationWidth + newAssistantWidth + analyticsWidth;
      if (totalUsed <= 100) {
        // Update the layout store instead of local state
        layoutActions.updateComponentWidths({
          conversation: newConversationWidth,
          assistant: newAssistantWidth,
          analytics: analyticsWidth
        });
      }
    } else if (activeHandle === 'assistant-analytics') {
      // Resizing between assistant and analytics panels
      const newAssistantWidth = Math.max(30, Math.min(70, startWidths.assistant + deltaPercent));
      const newAnalyticsWidth = Math.max(10, Math.min(40, startWidths.analytics - deltaPercent));
      
      // Ensure total doesn't exceed available space
      const totalUsed = conversationWidth + newAssistantWidth + newAnalyticsWidth;
      if (totalUsed <= 100) {
        // Update the layout store instead of local state
        layoutActions.updateComponentWidths({
          conversation: conversationWidth,
          assistant: newAssistantWidth,
          analytics: newAnalyticsWidth
        });
      }
    }
  }
  
  function stopResize() {
    isDragging = false;
    activeHandle = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
  
  onMount(() => {
    // Cleanup on unmount
    return () => {
      if (isDragging) {
        stopResize();
      }
    };
  });
</script>

<svelte:head>
  <title>Spiked AI Console</title>
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
        <button class="px-5 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500">Console</button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Recordings</button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Analytics</button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Settings</button>
      </nav>
    </div>
    <div class="flex items-center space-x-4">
      <!-- Quick Layouts -->
      <QuickLayouts />
      
      <div class="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
      
      <!-- Layout Selector -->
      <LayoutSelector on:layoutChanged={handleLayoutChanged} />
      
      <!-- Panel Controls Toggle -->
      <button 
        class="p-2.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600 {showPanelControls ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-700' : ''}" 
        on:click={togglePanelControls}
        aria-label="Toggle panel controls"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7m0-18L5 12l7 7"/>
        </svg>
      </button>
      
      <div class="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
      
      <!-- Mode Toggle -->
      <div class="flex items-center space-x-2 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg border border-gray-200 dark:border-gray-600">
        <button 
          class={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 ${
            currentMode === 'microphone' 
              ? 'bg-blue-600 text-white shadow-sm' 
              : 'text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
          on:click={() => toggleMode('microphone')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <span>Mic</span>
        </button>
        <button 
          class={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 ${
            currentMode === 'meeting' 
              ? 'bg-green-600 text-white shadow-sm' 
              : 'text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
          on:click={() => toggleMode('meeting')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
            <path d="M19.5 10.5c0 7-7.5 13-7.5 13s-7.5-6-7.5-13a7.5 7.5 0 0 1 15 0Z"/>
          </svg>
          <span>Meeting</span>
        </button>
      </div>
      <button 
        class="p-2.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600" 
        on:click={() => $darkMode = !$darkMode} 
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
  
  <div class="flex-1 p-6 gap-0 flex overflow-hidden" bind:this={containerEl}>
    <!-- Panel Controls Sidebar -->
    {#if showPanelControls}
      <div class="w-80 h-full overflow-y-auto pr-4 flex-shrink-0">
        <ComponentToggle on:componentToggled={handleComponentToggled} />
      </div>
    {/if}
    
    <!-- Left Panel - Conversation or Meeting -->
    {#if conversationEnabled}
      <div class="h-full overflow-hidden flex flex-col" style="width: {conversationWidth}%;">
        {#if currentMode === 'microphone'}
          <ConversationPanel 
            on:messageClick={handleConversationMessageClick}
            on:messageDrop={handleConversationDrop}
            on:questionDetected={handleQuestionDetected}
            on:sendToAssistant={handleSendToAssistant}
          />
        {:else if currentMode === 'meeting'}
          <MeetingPanel 
            on:sendToAssistant={handleMeetingToAssistant}
          />
        {/if}
      </div>
    {/if}
    
    <!-- First Resize Handle (Between Conversation and Assistant) -->
    {#if conversationEnabled && assistantEnabled && enabledPanels > 1}
      <div class="flex-shrink-0 w-6 h-full flex items-center justify-center group relative">
        <button 
          class="w-1 h-full bg-gray-300 dark:bg-gray-600 group-hover:bg-blue-500 dark:group-hover:bg-blue-400 transition-colors cursor-col-resize relative border-0 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Resize conversation and assistant panels"
          on:mousedown={(e) => startResize(e, 'conversation-assistant')}
        >
          <!-- Resize handle with arrows -->
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
              <svg class="w-3 h-3 text-gray-600 dark:text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5L5 8l3 3M16 5l3 3-3 3M5 8h14"/>
              </svg>
            </div>
          </div>
        </button>
      </div>
    {/if}
    
    <!-- AI Assistant Panel -->
    {#if assistantEnabled}
      <div class="h-full overflow-hidden flex flex-col" style="width: {assistantWidth}%;">
        <AIAssistantPanel 
          on:questionSubmit={handleQuestionSubmit} 
          on:followUpQuestion={handleFollowUpQuestion}
        />
      </div>
    {/if}
    
    <!-- Second Resize Handle (Between Assistant and Analytics) -->
    {#if assistantEnabled && analyticsEnabled && enabledPanels > 1}
      <div class="flex-shrink-0 w-6 h-full flex items-center justify-center group relative">
        <button 
          class="w-1 h-full bg-gray-300 dark:bg-gray-600 group-hover:bg-blue-500 dark:group-hover:bg-blue-400 transition-colors cursor-col-resize relative border-0 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Resize assistant and analytics panels"
          on:mousedown={(e) => startResize(e, 'assistant-analytics')}
        >
          <!-- Resize handle with arrows -->
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
              <svg class="w-3 h-3 text-gray-600 dark:text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5L5 8l3 3M16 5l3 3-3 3M5 8h14"/>
              </svg>
            </div>
          </div>
        </button>
      </div>
    {/if}
    
    <!-- Analytics Panel -->
    {#if analyticsEnabled}
      <div class="h-full overflow-hidden flex flex-col" style="width: {analyticsWidth}%;">
        <AnalyticsPanel />
      </div>
    {/if}
  </div>
</div>

<style>
  /* Prevent text selection during drag */
  .dragging {
    user-select: none;
  }
  
  /* Enhanced cursor styles */
  .cursor-col-resize:hover {
    cursor: col-resize;
  }
  
  /* Smooth transitions for width changes */
  .h-full.overflow-hidden.flex.flex-col {
    transition: width 0.1s ease-out;
  }
  
  /* Handle hover effects */
  .group:hover .w-1 {
    width: 0.25rem;
  }
</style>
