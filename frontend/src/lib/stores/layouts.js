import { writable, derived } from 'svelte/store';

// Default layout configurations
const defaultLayouts = {
  'full-console': {
    id: 'full-console',
    name: 'Full Console',
    description: 'All panels visible with conversation, assistant, and analytics',
    components: {
      conversation: { enabled: true, width: 28.57 },
      assistant: { enabled: true, width: 57.14 },
      analytics: { enabled: true, width: 14.29 }
    },
    modes: ['microphone', 'meeting']
  },
  'focused-assistant': {
    id: 'focused-assistant',
    name: 'Focused Assistant',
    description: 'Conversation and assistant only, no analytics',
    components: {
      conversation: { enabled: true, width: 35 },
      assistant: { enabled: true, width: 65 },
      analytics: { enabled: false, width: 0 }
    },
    modes: ['microphone', 'meeting']
  },
  'analytics-dashboard': {
    id: 'analytics-dashboard',
    name: 'Analytics Dashboard',
    description: 'Assistant and analytics focused for data analysis',
    components: {
      conversation: { enabled: false, width: 0 },
      assistant: { enabled: true, width: 70 },
      analytics: { enabled: true, width: 30 }
    },
    modes: ['microphone', 'meeting']
  },
  'conversation-only': {
    id: 'conversation-only',
    name: 'Conversation Only',
    description: 'Just the conversation panel for pure transcription',
    components: {
      conversation: { enabled: true, width: 100 },
      assistant: { enabled: false, width: 0 },
      analytics: { enabled: false, width: 0 }
    },
    modes: ['microphone', 'meeting']
  },
  'assistant-only': {
    id: 'assistant-only',
    name: 'Assistant Only',
    description: 'Just the AI assistant for pure Q&A',
    components: {
      conversation: { enabled: false, width: 0 },
      assistant: { enabled: true, width: 100 },
      analytics: { enabled: false, width: 0 }
    },
    modes: ['microphone', 'meeting']
  },
  'split-screen': {
    id: 'split-screen',
    name: 'Split Screen',
    description: 'Equal split between conversation and assistant',
    components: {
      conversation: { enabled: true, width: 50 },
      assistant: { enabled: true, width: 50 },
      analytics: { enabled: false, width: 0 }
    },
    modes: ['microphone', 'meeting']
  }
};

// Custom layouts created by user
const storedCustomLayouts = typeof localStorage !== 'undefined' && localStorage.getItem('customLayouts');
const customLayouts = writable(storedCustomLayouts ? JSON.parse(storedCustomLayouts) : {});

// Current active layout
const storedActiveLayout = typeof localStorage !== 'undefined' && localStorage.getItem('activeLayout');
export const activeLayout = writable(storedActiveLayout || 'full-console');

// All available layouts (default + custom)
export const availableLayouts = derived(
  [customLayouts],
  ([$customLayouts]) => ({
    ...defaultLayouts,
    ...$customLayouts
  })
);

// Current layout configuration
export const currentLayoutConfig = derived(
  [activeLayout, availableLayouts],
  ([$activeLayout, $availableLayouts]) => $availableLayouts[$activeLayout] || defaultLayouts['full-console']
);

// Component widths derived from current layout
export const componentWidths = derived(
  [currentLayoutConfig],
  ([$currentLayoutConfig]) => {
    const components = $currentLayoutConfig.components;
    
    // Normalize widths for enabled components only
    const enabledComponents = Object.entries(components).filter(([_, config]) => config.enabled);
    const totalWidth = enabledComponents.reduce((sum, [_, config]) => sum + config.width, 0);
    
    if (totalWidth === 0 || enabledComponents.length === 0) {
      return { conversation: 0, assistant: 0, analytics: 0 };
    }
    
    // Normalize to 100%
    const normalizedWidths = {};
    enabledComponents.forEach(([component, config]) => {
      normalizedWidths[component] = (config.width / totalWidth) * 100;
    });
    
    // Set disabled components to 0
    Object.keys(components).forEach(component => {
      if (!components[component].enabled) {
        normalizedWidths[component] = 0;
      }
    });
    
    return {
      conversation: normalizedWidths.conversation || 0,
      assistant: normalizedWidths.assistant || 0,
      analytics: normalizedWidths.analytics || 0
    };
  }
);

// Store subscriptions to persist data
customLayouts.subscribe(value => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('customLayouts', JSON.stringify(value));
  }
});

activeLayout.subscribe(value => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('activeLayout', value);
  }
});

// Layout management functions
export const layoutActions = {
  // Switch to a layout
  switchLayout: (layoutId) => {
    activeLayout.set(layoutId);
  },
  
  // Create a new custom layout
  createLayout: (layout) => {
    customLayouts.update(layouts => ({
      ...layouts,
      [layout.id]: layout
    }));
  },
  
  // Update an existing layout
  updateLayout: (layoutId, updates) => {
    customLayouts.update(layouts => ({
      ...layouts,
      [layoutId]: {
        ...layouts[layoutId],
        ...updates
      }
    }));
  },
  
  // Delete a custom layout
  deleteLayout: (layoutId) => {
    customLayouts.update(layouts => {
      const newLayouts = { ...layouts };
      delete newLayouts[layoutId];
      return newLayouts;
    });
    
    // If we're deleting the active layout, switch to default
    activeLayout.update(current => 
      current === layoutId ? 'full-console' : current
    );
  },
  
  // Update component widths for current layout
  updateComponentWidths: (widths) => {
    const current = activeLayout.get();
    const layouts = availableLayouts.get();
    const currentLayout = layouts[current];
    
    if (!currentLayout) return;
    
    const updatedComponents = { ...currentLayout.components };
    Object.entries(widths).forEach(([component, width]) => {
      if (updatedComponents[component]) {
        updatedComponents[component].width = width;
      }
    });
    
    if (defaultLayouts[current]) {
      // Can't modify default layouts, create a custom variant
      const customId = `${current}-custom-${Date.now()}`;
      layoutActions.createLayout({
        ...currentLayout,
        id: customId,
        name: `${currentLayout.name} (Custom)`,
        components: updatedComponents
      });
      layoutActions.switchLayout(customId);
    } else {
      // Update custom layout
      layoutActions.updateLayout(current, {
        components: updatedComponents
      });
    }
  },
  
  // Toggle component visibility
  toggleComponent: (componentName) => {
    const current = activeLayout.get();
    const layouts = availableLayouts.get();
    const currentLayout = layouts[current];
    
    if (!currentLayout) return;
    
    const updatedComponents = { ...currentLayout.components };
    if (updatedComponents[componentName]) {
      updatedComponents[componentName].enabled = !updatedComponents[componentName].enabled;
      
      // If disabling, set width to 0
      if (!updatedComponents[componentName].enabled) {
        updatedComponents[componentName].width = 0;
      } else {
        // If enabling and width is 0, give it a default width
        if (updatedComponents[componentName].width === 0) {
          const defaultWidth = componentName === 'conversation' ? 30 : 
                             componentName === 'assistant' ? 50 : 20;
          updatedComponents[componentName].width = defaultWidth;
        }
      }
    }
    
    if (defaultLayouts[current]) {
      // Can't modify default layouts, create a custom variant
      const customId = `${current}-custom-${Date.now()}`;
      layoutActions.createLayout({
        ...currentLayout,
        id: customId,
        name: `${currentLayout.name} (Custom)`,
        components: updatedComponents
      });
      layoutActions.switchLayout(customId);
    } else {
      // Update custom layout
      layoutActions.updateLayout(current, {
        components: updatedComponents
      });
    }
  },
  
  // Duplicate a layout
  duplicateLayout: (layoutId, newName) => {
    const layouts = availableLayouts.get();
    const originalLayout = layouts[layoutId];
    
    if (!originalLayout) return;
    
    const newId = `custom-${Date.now()}`;
    layoutActions.createLayout({
      ...originalLayout,
      id: newId,
      name: newName || `${originalLayout.name} Copy`
    });
    
    return newId;
  },
  
  // Reset to default layouts
  resetToDefaults: () => {
    customLayouts.set({});
    activeLayout.set('full-console');
  }
};

// Helper to get layout by ID
export const getLayout = (layoutId) => {
  const layouts = availableLayouts.get();
  return layouts[layoutId];
};

// Helper to check if layout is custom
export const isCustomLayout = (layoutId) => {
  return !defaultLayouts[layoutId];
};
