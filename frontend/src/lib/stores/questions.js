import { writable, derived } from 'svelte/store';

function createQuestionsStore() {
  const { subscribe, update } = writable({
    questions: [],
    loading: false
  });

  return {
    subscribe,
    
    addQuestion: (question, loading = true) => {
      update(state => {
        // Check if the question already exists
        const exists = state.questions.some(q => q.text === question);
        if (exists) return state;
        
        return {
          ...state,
          questions: [
            ...state.questions,
            { 
              id: Date.now().toString(),
              text: question, 
              answer: null,
              intent: null,
              sentiment: null,
              informationGap: null,
              sources: [],
              loading: loading,
              timestamp: new Date().toISOString()
            }
          ],
          loading
        };
      });
    },
    
    updateAnswer: (question, data) => {
      update(state => {
        const updatedQuestions = state.questions.map(q => {
          if (q.text === question) {
            return { 
              ...q, 
              answer: data.response || data,
              intent: data.intent || null,
              sentiment: data.sentiment || null,
              informationGap: data.information_gap || null,
              sources: (data.meta && data.meta.sources) || [],
              loading: false
            };
          }
          return q;
        });
        
        return {
          ...state,
          questions: updatedQuestions,
          loading: false
        };
      });
    },

    updateEnhancedAnswer: (question, data) => {
      update(state => {
        const updatedQuestions = state.questions.map(q => {
          if (q.text === question) {
            return { 
              ...q, 
              answer: data.straightforward_answer,
              intent: data.intent || null,
              sentiment: data.sentiment || null,
              informationGap: data.information_gap || null,
              sources: data.sources || [],
              statistics: data.statistics || [],
              salesPoints: data.sales_points || [],
              starResponse: data.star_response || null,
              comparisonTable: data.comparison_table || null,
              relevantBullets: data.relevant_bullets || [],
              terminologyExplainer: data.terminology_explainer || null,
              analogiesOrMetaphors: data.analogies_or_metaphors || null,
              customerStorySnippet: data.customer_story_snippet || null,
              pricingInsight: data.pricing_insight || null,
              escalationFlag: data.escalation_flag || false,
              followUpQuestions: data.follow_up_questions || [],
              longformResponse: data.longform_response || null,
              webSearchResults: data.web_search_results || [],
              confidenceScore: data.confidence_score || 0,
              loading: false
            };
          }
          return q;
        });
        
        return {
          ...state,
          questions: updatedQuestions,
          loading: false
        };
      });
    },
    
    updateEnhancedAnswer: (question, data) => {
      update(state => {
        const updatedQuestions = state.questions.map(q => {
          if (q.text === question) {
            return { 
              ...q, 
              // Legacy fields for backward compatibility
              answer: data.response || data.straightforward_answer,
              intent: data.intent || null,
              sentiment: data.sentiment || null,
              informationGap: data.information_gap || null,
              sources: (data.meta && data.meta.sources) || [],
              
              // Enhanced RAG fields
              straightforwardAnswer: data.straightforward_answer || null,
              starResponse: data.star_response || null,
              comparisonTable: data.comparison_table || null,
              relevantBullets: data.relevant_bullets || [],
              statisticsObj: data.statistics || {},
              terminologyExplainer: data.terminology_explainer || null,
              analogiesOrMetaphors: data.analogies_or_metaphors || null,
              customerStorySnippet: data.customer_story_snippet || null,
              pricingInsight: data.pricing_insight || null,
              escalationFlag: data.escalation_flag || false,
              followUpQuestions: data.follow_up_questions || [],
              longformResponse: data.longform_response || null,
              salesPoints: data.salesPoints || data.relevant_bullets || [],
              statistics: Object.entries(data.statistics || {}).map(([key, value]) => value) || [],
              loading: false
            };
          }
          return q;
        });
        
        return {
          ...state,
          questions: updatedQuestions,
          loading: false
        };
      });
    },
    
    removeQuestion: (id) => {
      update(state => ({
        ...state,
        questions: state.questions.filter(q => q.id !== id)
      }));
    },
    
    clearQuestions: () => {
      update(() => ({ questions: [], loading: false }));
    }
  };
}

export const questionsStore = createQuestionsStore();

// Derived store for the most recent question
export const currentQuestion = derived(
  questionsStore,
  $store => {
    const questions = $store.questions;
    return questions.length > 0 ? questions[questions.length - 1] : null;
  }
);