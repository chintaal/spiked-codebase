<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { darkMode } from '$lib/stores/ui.js';

  // Stores using Svelte 5 runes
  let files = $state([]);
  let uploading = $state(false);
  let searchResults = $state([]);
  let searchQuery = $state('');
  let isSearching = $state(false);
  let selectedFile = $state(null);
  let showUploadModal = $state(false);
  let databaseStats = $state({});

  // Component state
  let dragOver = $state(false);
  let uploadProgress = $state(0);
  let fileInput;
  let searchInput;
  let selectedFileForSearch = $state('');
  let dragCounter = $state(0);
  let selectedFileForUpload = $state(null);
  let fileDescription = $state('');

  onMount(() => {
    loadFiles();
    loadDatabaseStats();
  });

  async function loadFiles() {
    try {
      const response = await fetch('http://localhost:8000/api/files/list');
      const data = await response.json();
      
      if (response.ok) {
        files = data.files;
        databaseStats = data.database_stats;
      }
    } catch (error) {
      console.error('Error loading files:', error);
    }
  }

  async function loadDatabaseStats() {
    try {
      const response = await fetch('http://localhost:8000/api/files/stats');
      const data = await response.json();
      
      if (response.ok) {
        databaseStats = data;
      }
    } catch (error) {
      console.error('Error loading database stats:', error);
    }
  }

  async function uploadFile(file, description = '') {
    uploading = true;
    uploadProgress = 0;

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (description) {
        formData.append('description', description);
      }

      const response = await fetch('http://localhost:8000/api/files/upload', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        showUploadModal = false;
        await loadFiles();
        await loadDatabaseStats();
        alert(`File "${file.name}" uploaded successfully!`);
      } else {
        alert(`Upload failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.message}`);
    } finally {
      uploading = false;
      uploadProgress = 0;
    }
  }

  async function deleteFile(fileId, filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      const response = await fetch(`http://localhost:8000/api/files/delete/${fileId}`, {
        method: 'DELETE'
      });

      const result = await response.json();

      if (response.ok) {
        await loadFiles();
        await loadDatabaseStats();
        alert('File deleted successfully!');
      } else {
        alert(`Delete failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Delete failed: ${error.message}`);
    }
  }

  async function searchFiles() {
    const query = searchQuery.trim();
    if (!query) return;

    isSearching = true;

    try {
      const response = await fetch('http://localhost:8000/api/files/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          limit: 20,
          file_id: selectedFileForSearch || null
        })
      });

      const result = await response.json();

      if (response.ok) {
        searchResults = result.results;
      } else {
        alert(`Search failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Search error:', error);
      alert(`Search failed: ${error.message}`);
    } finally {
      isSearching = false;
    }
  }

  async function viewFileDetails(fileId) {
    try {
      const response = await fetch(`http://localhost:8000/api/files/details/${fileId}`);
      const result = await response.json();

      if (response.ok) {
        selectedFile = result.file_details;
      } else {
        alert(`Failed to load file details: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error loading file details:', error);
      alert(`Failed to load file details: ${error.message}`);
    }
  }

  async function downloadProcessedFile(fileId, filename) {
    try {
      const response = await fetch(`http://localhost:8000/api/files/download/${fileId}`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const result = await response.json();
        alert(`Download failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Download error:', error);
      alert(`Download failed: ${error.message}`);
    }
  }

  function handleDragEnter(e) {
    e.preventDefault();
    dragCounter++;
    dragOver = true;
  }

  function handleDragLeave(e) {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
      dragOver = false;
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDrop(e) {
    e.preventDefault();
    dragOver = false;
    dragCounter = 0;

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      handleFileSelect(droppedFiles[0]);
    }
  }

  function handleFileSelect(file) {
    showUploadModal = true;
    selectedFileForUpload = file;
  }

  function handleFileInputChange(e) {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }

  function closeModal() {
    showUploadModal = false;
    selectedFileForUpload = null;
    fileDescription = '';
  }

  function confirmUpload() {
    if (selectedFileForUpload) {
      uploadFile(selectedFileForUpload, fileDescription);
      closeModal();
    }
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
  }

  function getFileIcon(fileType) {
    const iconMap = {
      'PDF Document': '📄',
      'Word Document': '📝',
      'PowerPoint Presentation': '📊',
      'Text File': '📃',
      'Markdown File': '📋',
      'JPEG Image': '🖼️',
      'PNG Image': '🖼️',
      'GIF Image': '🖼️'
    };
    return iconMap[fileType] || '📁';
  }
  
  // Navigation functions
  function navigateToConsole() {
    goto('/console');
  }
  
  function navigateToCache() {
    goto('/cache');
  }
  
  function navigateToFiles() {
    goto('/files');
  }
</script>

<svelte:head>
  <title>Document Management - Spiked AI Console</title>
  <meta name="description" content="Manage documents and files for the Spiked AI system" />
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
    <div class="flex-1 flex justify-center max-w-xl">
      <nav class="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1.5 rounded-lg border border-gray-200 dark:border-gray-600">
        <button 
          class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors"
          onclick={navigateToConsole}
        >
          Console
        </button>
        <button 
          class="px-5 py-2 text-sm font-semibold rounded-lg bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500 flex items-center space-x-1"
          onclick={navigateToFiles}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14,2 14,8 20,8"></polyline>
          </svg>
          <span>Files</span>
        </button>
        <button 
          class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors flex items-center space-x-1"
          onclick={navigateToCache}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
            <circle cx="9" cy="9" r="2"/>
            <path d="m21 15-3.086-3.086a2 2 0 0 0-1.414-.586H14l-3-3h-2.5a2 2 0 0 0-1.414.586L4 12.414"/>
          </svg>
          <span>Cache</span>
        </button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Recordings</button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Analytics</button>
        <button class="px-5 py-2 text-sm font-medium rounded-lg text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 transition-colors">Settings</button>
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
          📁 Document Management
        </h2>
        <p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
          Upload, manage, and search through your documents for the Spiked AI knowledge base
        </p>
      </div>

      <!-- Database Stats -->
      {#if databaseStats && Object.keys(databaseStats).length > 0}
        <div class="mb-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">📊 Database Statistics</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="text-center">
              <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{databaseStats.total_files || 0}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Total Files</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-green-600 dark:text-green-400">{databaseStats.total_chunks || 0}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Total Chunks</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">{formatFileSize(databaseStats.total_size || 0)}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Total Size</div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Search Section -->
      <div class="mb-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">🔍 Search Documents</h3>
        <div class="flex gap-4 mb-4">
          <input
            bind:this={searchInput}
            bind:value={searchQuery}
            type="text"
            placeholder="Search for content across all documents..."
            class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
            onkeydown={(e) => e.key === 'Enter' && searchFiles()}
          />
          <select
            bind:value={selectedFileForSearch}
            class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-gray-100"
          >
            <option value="">All Files</option>
            {#each files as file}
              <option value={file.file_id}>{file.original_filename}</option>
            {/each}
          </select>
          <button
            class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
            disabled={isSearching || !searchQuery.trim()}
            onclick={searchFiles}
          >
            {#if isSearching}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            {:else}
              Search
            {/if}
          </button>
        </div>

        <!-- Search Results -->
        {#if searchResults.length > 0}
          <div class="mt-6">
            <h4 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Search Results ({searchResults.length})</h4>
            <div class="space-y-4 max-h-64 overflow-y-auto">
              {#each searchResults as result}
                <div class="p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
                  <div class="flex justify-between items-start mb-2">
                    <span class="font-medium text-gray-900 dark:text-gray-100">{result.filename}</span>
                    <span class="text-sm bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                      Score: {(result.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{result.content}</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <!-- File Upload Zone -->
      <div
        class="mb-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center transition-colors hover:border-blue-500 dark:hover:border-blue-400 cursor-pointer {dragOver ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-gray-800'}"
        role="button"
        tabindex="0"
        ondragenter={handleDragEnter}
        ondragleave={handleDragLeave}
        ondragover={handleDragOver}
        ondrop={handleDrop}
        onclick={() => fileInput.click()}
        onkeydown={(e) => e.key === 'Enter' && fileInput.click()}
      >
        <div class="pointer-events-none">
          <div class="text-4xl mb-4">📤</div>
          <p class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Drop files here or click to upload</p>
          <p class="text-sm text-gray-600 dark:text-gray-400">Supports: PDF, DOCX, TXT, MD, PPTX, Images (Max 50MB)</p>
        </div>
        <input
          bind:this={fileInput}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md,.pptx,.ppt,.jpg,.jpeg,.png,.gif,.bmp"
          class="hidden"
          onchange={handleFileInputChange}
        />
      </div>

      <!-- Files List -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            📋 Uploaded Documents ({files.length})
          </h3>
        </div>
        
        {#if files.length === 0}
          <div class="px-6 py-12 text-center">
            <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
              <svg class="w-8 h-8 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <p class="text-gray-500 dark:text-gray-400 mb-4">No documents uploaded yet</p>
            <button 
              class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              onclick={() => showUploadModal = true}
            >
              Upload Your First Document
            </button>
          </div>
        {:else}
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 p-6">
            {#each files as file}
              <div class="border border-gray-200 dark:border-gray-600 rounded-lg p-6 hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between mb-4">
                  <div class="flex items-center gap-3">
                    <div class="text-2xl">{getFileIcon(file.file_type)}</div>
                    <div>
                      <h4 class="font-medium text-gray-900 dark:text-gray-100 break-words">{file.original_filename}</h4>
                      <p class="text-sm text-gray-600 dark:text-gray-400">{file.file_type}</p>
                    </div>
                  </div>
                </div>
                
                <div class="space-y-2 mb-4">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Size:</span>
                    <span class="text-gray-900 dark:text-gray-100">{formatFileSize(file.file_size)}</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Uploaded:</span>
                    <span class="text-gray-900 dark:text-gray-100">{formatDate(file.created_at)}</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Chunks:</span>
                    <span class="text-gray-900 dark:text-gray-100">{file.chunk_count || 0}</span>
                  </div>
                  {#if file.description}
                    <div class="text-sm">
                      <span class="text-gray-600 dark:text-gray-400">Description:</span>
                      <p class="text-gray-900 dark:text-gray-100 mt-1 p-2 bg-gray-50 dark:bg-gray-700 rounded text-xs italic">{file.description}</p>
                    </div>
                  {/if}
                </div>
                
                <div class="flex gap-2 flex-wrap">
                  <button
                    class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                    onclick={() => viewFileDetails(file.file_id)}
                  >
                    👁️ View
                  </button>
                  <button
                    class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
                    onclick={() => downloadProcessedFile(file.file_id, file.original_filename)}
                  >
                    📥 Download
                  </button>
                  <button
                    class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                    onclick={() => deleteFile(file.file_id, file.original_filename)}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onclick={closeModal}>
    <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4" onclick={(e) => e.stopPropagation()}>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Upload Document</h3>
        <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" onclick={closeModal}>
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <div class="mb-4">
        {#if selectedFileForUpload}
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg mb-4">
            <p class="text-sm text-gray-900 dark:text-gray-100"><strong>File:</strong> {selectedFileForUpload.name}</p>
            <p class="text-sm text-gray-600 dark:text-gray-400"><strong>Size:</strong> {formatFileSize(selectedFileForUpload.size)}</p>
          </div>
        {/if}
        
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Description (optional)
        </label>
        <textarea
          bind:value={fileDescription}
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
          rows="3"
          placeholder="Enter a description for this file..."
        ></textarea>
      </div>

      {#if uploading}
        <div class="mb-4 text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Uploading...</p>
          {#if uploadProgress > 0}
            <div class="mt-2 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
              <div class="bg-blue-600 h-2 rounded-full transition-all" style="width: {uploadProgress}%"></div>
            </div>
          {/if}
        </div>
      {/if}

      <div class="flex gap-3 justify-end">
        <button
          class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          disabled={uploading}
          onclick={closeModal}
        >
          Cancel
        </button>
        <button
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          disabled={!selectedFileForUpload || uploading}
          onclick={confirmUpload}
        >
          Upload
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- File Details Modal -->
{#if selectedFile}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onclick={() => selectedFile = null}>
    <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100">File Details</h3>
        <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" onclick={() => selectedFile = null}>
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <h4 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Metadata</h4>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Filename:</span>
              <span class="text-gray-900 dark:text-gray-100 font-medium">{selectedFile.original_filename}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Type:</span>
              <span class="text-gray-900 dark:text-gray-100">{selectedFile.file_type}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Size:</span>
              <span class="text-gray-900 dark:text-gray-100">{formatFileSize(selectedFile.file_size)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Chunks:</span>
              <span class="text-gray-900 dark:text-gray-100">{selectedFile.chunks?.length || 0}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Uploaded:</span>
              <span class="text-gray-900 dark:text-gray-100">{formatDate(selectedFile.created_at)}</span>
            </div>
          </div>
        </div>
        
        {#if selectedFile.description}
          <div>
            <h4 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Description</h4>
            <p class="text-gray-600 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">{selectedFile.description}</p>
          </div>
        {/if}
      </div>

      {#if selectedFile.chunks && selectedFile.chunks.length > 0}
        <div>
          <h4 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">Content Chunks ({selectedFile.chunks.length})</h4>
          <div class="space-y-3 max-h-96 overflow-y-auto">
            {#each selectedFile.chunks as chunk, index}
              <div class="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                <div class="flex justify-between items-center mb-2">
                  <span class="font-medium text-gray-900 dark:text-gray-100">Chunk {index + 1}</span>
                  <span class="text-sm text-gray-600 dark:text-gray-400">{chunk.content.length} characters</span>
                </div>
                <p class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{chunk.content.substring(0, 200)}...</p>
              </div>
            {/each}
          </div>
        </div>
      {/if}
      
      <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
        <button
          class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
          onclick={() => downloadProcessedFile(selectedFile.file_id, selectedFile.original_filename)}
        >
          📥 Download
        </button>
        <button
          class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          onclick={() => selectedFile = null}
        >
          Close
        </button>
      </div>
    </div>
  </div>
{/if}