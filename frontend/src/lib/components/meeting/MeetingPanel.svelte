<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { meetingStore, meetingActions, meetingUtils } from '$lib/stores/meeting.js';
  import { vexaClient } from '$lib/utils/vexaClient.js';
  import { darkMode } from '$lib/stores/ui.js';
  
  const dispatch = createEventDispatcher();
  
  // Component state
  let meetingUrl = '';
  let isValidUrl = false;
  let transcriptContainer;
  let pollInterval = null;
  let runningBots = []; // Track running bots
  
  // Meeting configuration
  let botName = 'Spiked AI Bot';
  let language = 'en';
  let autoRefresh = true;
  let refreshInterval = 3000; // 3 seconds
  
  // UI state
  let showMeetingHistory = false;
  let showBotConfig = false;
  
  // Reactive statements
  $: {
    const validation = vexaClient.constructor.validateMeetingUrl(meetingUrl);
    isValidUrl = validation.isValid;
    if (validation.isValid) {
      meetingActions.setMeetingDetails(validation.meetingId, validation.platform);
    }
  }
  
  $: formattedTranscript = meetingUtils.formatTranscript($meetingStore.transcript);
  $: groupedTranscript = meetingUtils.groupBySpeaker(formattedTranscript);
  
  onMount(async () => {
    // Load meeting history
    await loadMeetingHistory();
    
    // Load running bots
    await loadRunningBots();
    
    // Set initial bot config
    meetingActions.setBotConfig(botName, language);
  });
  
  onDestroy(() => {
    // Clean up polling
    if (pollInterval) {
      clearInterval(pollInterval);
    }
  });
  
  // Load meeting history
  async function loadMeetingHistory() {
    try {
      meetingActions.setLoading(true);
      const meetings = await vexaClient.listMeetings();
      meetingActions.setMeetings(meetings);
    } catch (error) {
      console.error('Failed to load meeting history:', error);
      meetingActions.setError('Failed to load meeting history');
    } finally {
      meetingActions.setLoading(false);
    }
  }
  
  // Load running bots
  async function loadRunningBots() {
    try {
      const result = await vexaClient.getBotStatus();
      runningBots = result.running_bots || [];
    } catch (error) {
      console.error('Failed to load running bots:', error);
    }
  }
  
  // Start meeting bot
  async function startMeetingBot() {
    if (!isValidUrl) return;
    
    try {
      meetingActions.setLoading(true);
      meetingActions.clearError();
      meetingActions.setBotStatus('requesting');
      
      const response = await vexaClient.requestBot(
        $meetingStore.meetingId,
        $meetingStore.platform,
        {
          language: $meetingStore.language,
          bot_name: $meetingStore.botName
        }
      );
      
      meetingActions.setCurrentMeeting(response);
      meetingActions.setBotStatus('active', response);
      
      // Start polling for transcript updates
      if (autoRefresh) {
        startTranscriptPolling();
      }
      
      // Initial transcript fetch
      await fetchTranscript();
      
    } catch (error) {
      console.error('Failed to start meeting bot:', error);
      meetingActions.setError(`Failed to start meeting bot: ${error.message}`);
      meetingActions.setBotStatus('error');
      
      // If it's a conflict error, reload running bots to show current state
      if (error.message.includes('Conflict') || error.message.includes('concurrent') || error.message.includes('already')) {
        await loadRunningBots();
      }
    } finally {
      meetingActions.setLoading(false);
    }
  }
  
  // Stop meeting bot
  async function stopMeetingBot() {
    try {
      meetingActions.setLoading(true);
      meetingActions.setBotStatus('stopping');
      
      await vexaClient.stopBot($meetingStore.meetingId, $meetingStore.platform);
      
      // Stop polling
      stopTranscriptPolling();
      
      meetingActions.setBotStatus('stopped');
      meetingActions.setCurrentMeeting(null);
      
      // Reload meeting history
      await loadMeetingHistory();
      
      // Reload running bots
      await loadRunningBots();
      
    } catch (error) {
      console.error('Failed to stop meeting bot:', error);
      meetingActions.setError(`Failed to stop meeting bot: ${error.message}`);
    } finally {
      meetingActions.setLoading(false);
    }
  }
  
  // Stop all running bots
  async function stopAllBots() {
    try {
      meetingActions.setLoading(true);
      const result = await vexaClient.stopAllBots();
      meetingActions.setError(`Stopped ${result.stoppedCount} running bot(s). You can now start a new bot.`);
      await loadRunningBots();
    } catch (error) {
      console.error('Failed to stop all bots:', error);
      meetingActions.setError(`Failed to stop running bots: ${error.message}`);
    } finally {
      meetingActions.setLoading(false);
    }
  }
  
  // Fetch transcript
  async function fetchTranscript() {
    try {
      const transcript = await vexaClient.getTranscript(
        $meetingStore.meetingId,
        $meetingStore.platform
      );
      
      if (transcript && transcript.segments) {
        meetingActions.updateTranscript(transcript.segments);
      }
    } catch (error) {
      console.error('Failed to fetch transcript:', error);
      // Don't show error for transcript fetch failures during polling
    }
  }
  
  // Start transcript polling
  function startTranscriptPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
    }
    
    pollInterval = setInterval(async () => {
      if ($meetingStore.botStatus === 'active') {
        await fetchTranscript();
      }
    }, refreshInterval);
    
    meetingActions.setTranscriptPolling(true);
  }
  
  // Stop transcript polling
  function stopTranscriptPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    meetingActions.setTranscriptPolling(false);
  }
  
  // Update bot configuration
  async function updateBotConfiguration() {
    try {
      meetingActions.setLoading(true);
      
      await vexaClient.updateBotConfig(
        $meetingStore.meetingId,
        $meetingStore.platform,
        {
          language: language,
          bot_name: botName
        }
      );
      
      meetingActions.setBotConfig(botName, language);
      showBotConfig = false;
      
    } catch (error) {
      console.error('Failed to update bot configuration:', error);
      meetingActions.setError(`Failed to update bot configuration: ${error.message}`);
    } finally {
      meetingActions.setLoading(false);
    }
  }
  
  // Send transcript to AI assistant
  function sendTranscriptToAssistant() {
    if ($meetingStore.transcript.length === 0) return;
    
    const transcriptText = $meetingStore.transcript
      .map(segment => `${segment.speaker}: ${segment.text}`)
      .join('\n');
    
    dispatch('sendToAssistant', {
      question: transcriptText,
      context: 'meeting_transcript'
    });
  }
  
  // Auto-scroll to bottom
  function scrollToBottom() {
    if (transcriptContainer && $meetingStore.autoScroll) {
      transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
    }
  }
  
  // Watch for transcript updates to auto-scroll
  $: if ($meetingStore.transcript.length > 0 && $meetingStore.autoScroll) {
    setTimeout(scrollToBottom, 100);
  }
  
  // Toggle auto refresh
  function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    if (autoRefresh && $meetingStore.botStatus === 'active') {
      startTranscriptPolling();
    } else {
      stopTranscriptPolling();
    }
  }
  
  // Format speaker name
  function formatSpeakerName(speaker) {
    if (!speaker) return 'Unknown';
    return speaker.charAt(0).toUpperCase() + speaker.slice(1);
  }
  
  // Get speaker color
  function getSpeakerColor(speaker) {
    const colors = [
      'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
      'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
      'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
      'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300',
      'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300'
    ];
    
    const hash = speaker.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);
    
    return colors[Math.abs(hash) % colors.length];
  }
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
  <header class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-green-600 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
            <path d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
            <path d="M19.5 10.5c0 7-7.5 13-7.5 13s-7.5-6-7.5-13a7.5 7.5 0 0 1 15 0Z"/>
          </svg>
        </div>
        <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">Meeting Bot</h2>
        <div class="flex items-center space-x-2">
          <span class={`inline-block w-3 h-3 rounded-full ${
            $meetingStore.botStatus === 'active' 
              ? 'bg-green-500' 
              : $meetingStore.botStatus === 'requesting' || $meetingStore.botStatus === 'stopping'
                ? 'bg-yellow-500' 
                : $meetingStore.botStatus === 'error'
                  ? 'bg-red-500'
                  : 'bg-gray-400'
          }`}></span>
          <span class="text-sm text-gray-600 dark:text-gray-400 capitalize">
            {$meetingStore.botStatus}
          </span>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <button 
          class="px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
          on:click={() => showBotConfig = !showBotConfig}
          title="Bot Configuration"
        >
          ⚙️
        </button>
        <button 
          class="px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
          on:click={() => showMeetingHistory = !showMeetingHistory}
          title="Meeting History"
        >
          📋
        </button>
        <button 
          class="px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
          on:click={loadRunningBots}
          title="Refresh bot status"
        >
          🔄
        </button>
        <div class="px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 rounded-full border">
          🌐 Live API
        </div>
        <button 
          class={`px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${autoRefresh ? 'bg-green-600 text-white border-green-600' : 'bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-500'}`}
          on:click={toggleAutoRefresh}
          title="Toggle auto-refresh"
        >
          {autoRefresh ? '🔄' : '⏸️'}
        </button>
      </div>
    </div>
  </header>

  <!-- Bot Configuration Panel -->
  {#if showBotConfig}
    <div class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
      <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">Bot Configuration</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="botName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Bot Name</label>
          <input 
            id="botName"
            type="text" 
            bind:value={botName}
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="Enter bot name"
          />
        </div>
        <div>
          <label for="language" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Language</label>
          <select 
            id="language"
            bind:value={language}
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="it">Italian</option>
            <option value="pt">Portuguese</option>
            <option value="ru">Russian</option>
            <option value="ja">Japanese</option>
            <option value="ko">Korean</option>
            <option value="zh">Chinese</option>
          </select>
        </div>
      </div>
      <div class="flex justify-end space-x-3 mt-4">
        <button 
          class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
          on:click={() => showBotConfig = false}
        >
          Cancel
        </button>
        <button 
          class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          on:click={updateBotConfiguration}
          disabled={$meetingStore.isLoading}
        >
          {$meetingStore.isLoading ? 'Updating...' : 'Update Bot'}
        </button>
      </div>
    </div>
  {/if}

  <!-- Meeting History -->
  {#if showMeetingHistory}
    <div class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 max-h-48 overflow-y-auto">
      <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">Recent Meetings</h3>
      {#if $meetingStore.meetings.length > 0}
        <div class="space-y-2">
          {#each $meetingStore.meetings as meeting}
            <div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
              <div class="flex-1">
                <div class="font-medium text-gray-800 dark:text-gray-100">
                  {meeting.data?.name || meeting.native_meeting_id}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {new Date(meeting.created_at).toLocaleString()}
                </div>
              </div>
              <button 
                class="px-3 py-1 text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                on:click={() => {
                  meetingUrl = `https://meet.google.com/${meeting.native_meeting_id}`;
                  showMeetingHistory = false;
                }}
              >
                Load
              </button>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-gray-500 dark:text-gray-400">No meetings found</p>
      {/if}
    </div>
  {/if}

  <!-- Meeting URL Input -->
  <div class="p-6 border-b border-gray-200 dark:border-gray-700">
    <div class="space-y-4">
      <div>
        <label for="meetingUrl" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Meeting URL
        </label>
        <div class="flex space-x-3">
          <input 
            type="url" 
            id="meetingUrl"
            bind:value={meetingUrl}
            placeholder="https://meet.google.com/xxx-xxxx-xxx"
            class={`flex-1 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${
              meetingUrl && !isValidUrl 
                ? 'border-red-300 dark:border-red-600' 
                : 'border-gray-300 dark:border-gray-600'
            }`}
          />
          {#if $meetingStore.botStatus === 'idle' || $meetingStore.botStatus === 'stopped' || $meetingStore.botStatus === 'error'}
            <button 
              class="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={startMeetingBot}
              disabled={!isValidUrl || $meetingStore.isLoading}
            >
              {$meetingStore.isLoading ? 'Starting...' : 'Start Bot'}
            </button>
          {:else}
            <button 
              class="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50"
              on:click={stopMeetingBot}
              disabled={$meetingStore.isLoading}
            >
              {$meetingStore.isLoading ? 'Stopping...' : 'Stop Bot'}
            </button>
          {/if}
        </div>
        {#if meetingUrl && !isValidUrl}
          <p class="text-red-600 dark:text-red-400 text-sm mt-2">
            Please enter a valid Google Meet URL
          </p>
        {/if}
        {#if $meetingStore.botStatus === 'requesting' || $meetingStore.botStatus === 'active'}
          <div class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm">
            <div class="flex items-center space-x-2">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 0-3-6.291V0C5.373 0 12 6.627 12 14h-4zm2-5.291A7.962 7.962 0 014 12H0c0-3.042 1.135-5.824 3-7.938l3 2.647z"></path>
              </svg>
              <span class="font-medium">
                {#if $meetingStore.botStatus === 'requesting'}
                  Bot requesting to join meeting...
                {:else}
                  Bot is active in meeting
                {/if}
              </span>
            </div>
            <p class="mt-2">
              {#if $meetingStore.botStatus === 'requesting'}
                ⏱️ <strong>Next step:</strong> Accept the bot's join request in Google Meet (~10 seconds)
              {:else}
                ✅ Bot joined successfully! Transcript will appear as people speak.
              {/if}
            </p>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Error Display -->
  {#if $meetingStore.error}
    <div class="mx-6 mt-4 p-4 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <span>⚠️</span>
        <span class="text-sm">{$meetingStore.error}</span>
      </div>
      <button 
        class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 text-lg"
        on:click={meetingActions.clearError}
      >
        ×
      </button>
    </div>
  {/if}

  <!-- Running Bots Warning -->
  {#if runningBots.length > 0}
    <div class="mx-6 mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-lg">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center space-x-2">
          <span>🤖</span>
          <span class="font-medium">Running Bots ({runningBots.length})</span>
        </div>
        <button 
          class="px-3 py-1 text-xs bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50"
          on:click={stopAllBots}
          disabled={$meetingStore.isLoading}
        >
          Stop All
        </button>
      </div>
      <div class="space-y-2">
        {#each runningBots as bot}
          <div class="flex items-center justify-between p-2 bg-white dark:bg-gray-700 rounded border">
            <div class="text-sm">
              <div class="font-medium">{bot.platform}: {bot.native_meeting_id}</div>
              <div class="text-gray-500 dark:text-gray-400">{bot.status}</div>
            </div>
            <button 
              class="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
              on:click={async () => {
                try {
                  await vexaClient.stopBot(bot.native_meeting_id, bot.platform);
                  await loadRunningBots();
                } catch (error) {
                  console.error('Failed to stop bot:', error);
                }
              }}
            >
              Stop
            </button>
          </div>
        {/each}
      </div>
      <p class="text-sm mt-2 opacity-80">
        You can only run 1 bot at a time. Stop an existing bot to start a new one.
      </p>
    </div>
  {/if}

  <!-- Transcript Display -->
  <div class="flex-1 overflow-hidden mx-6 my-6">
    <div class="h-full flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100">Live Transcript</h3>
        <div class="flex items-center space-x-4">
          {#if $meetingStore.transcript.length > 0}
            <button 
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              on:click={sendTranscriptToAssistant}
            >
              Send to AI Assistant
            </button>
          {/if}
          <label class="inline-flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              checked={$meetingStore.autoScroll}
              on:change={meetingActions.toggleAutoScroll}
              class="sr-only peer"
            />
            <div class="relative w-11 h-6 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 dark:peer-focus:ring-green-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
            <span class="ml-3 text-sm font-medium text-gray-700 dark:text-gray-300">Auto-scroll</span>
          </label>
        </div>
      </div>
      
      <div 
        class="flex-1 overflow-y-auto p-4 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600"
        bind:this={transcriptContainer}
      >
        {#if $meetingStore.transcript.length > 0}
          <div class="space-y-4">
            {#each groupedTranscript as group}
              <div class="flex space-x-3">
                <div class="flex-shrink-0">
                  <div class={`px-2 py-1 text-xs font-medium rounded-full ${getSpeakerColor(group.speaker)}`}>
                    {formatSpeakerName(group.speaker)}
                  </div>
                </div>
                <div class="flex-1 space-y-2">
                  {#each group.segments as segment}
                    <div class="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-200 dark:border-gray-600">
                      <p class="text-gray-800 dark:text-gray-200 mb-2">{segment.text}</p>
                      <div class="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
                        <span>{segment.formattedTime}</span>
                        {#if segment.confidence}
                          <span class="px-2 py-1 bg-gray-100 dark:bg-gray-600 rounded-full">
                            {Math.round(segment.confidence * 100)}% confidence
                          </span>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {:else if $meetingStore.botStatus === 'active'}
          <div class="h-full flex flex-col items-center justify-center text-center p-8">
            <div class="p-6 mb-6 bg-green-50 dark:bg-green-900/30 rounded-lg border border-green-200 dark:border-green-700">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600 dark:text-green-400 animate-pulse">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">Bot is Active</h3>
            <p class="text-gray-500 dark:text-gray-400 max-w-sm">
              The bot is in the meeting and listening. Transcript will appear here as participants speak.
            </p>
          </div>
        {:else}
          <div class="h-full flex flex-col items-center justify-center text-center p-8">
            <div class="p-6 mb-6 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500">
                <path d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/>
                <path d="M19.5 10.5c0 7-7.5 13-7.5 13s-7.5-6-7.5-13a7.5 7.5 0 0 1 15 0Z"/>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">No Active Meeting</h3>
            <p class="text-gray-500 dark:text-gray-400 max-w-sm">
              Enter a Google Meet URL above and click "Start Bot" to begin capturing meeting transcripts.
            </p>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
