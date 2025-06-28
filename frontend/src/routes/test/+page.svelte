<script>
  import { darkMode } from '$lib/stores/ui.js';
</script>

<div class="h-screen flex flex-col bg-gray-50">
  <div class="p-6">
    <h1 class="text-2xl font-bold">Test Page</h1>
    <p>Dark mode: {$darkMode}</p>
    <button 
      class="bg-blue-500 text-white px-4 py-2 rounded"
      onclick={() => $darkMode = !$darkMode}
    >
      Toggle Dark Mode
    </button>
  </div>
</div>
