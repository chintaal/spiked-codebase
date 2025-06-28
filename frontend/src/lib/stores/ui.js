import { writable } from 'svelte/store';

// Persistent dark mode preference
const storedDarkMode = typeof localStorage !== 'undefined' && localStorage.getItem('darkMode');
export const darkMode = writable(storedDarkMode === 'true');

// Subscribe to changes and store in localStorage
darkMode.subscribe(value => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('darkMode', value);
  }
});