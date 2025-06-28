/**
 * Advanced question detection utility
 * Detects questions in transcripts using various patterns and heuristics
 */

/**
 * Checks if text contains a question using multiple detection methods
 * @param {string} text - The text to analyze for questions
 * @param {boolean} includeImplicit - Whether to include implicit questions
 * @return {boolean} - Whether the text contains a question
 */
export function detectQuestion(text, includeImplicit = false) {
  if (!text || typeof text !== 'string') return false;
  
  const trimmedText = text.trim();
  
  // Skip very short texts that are unlikely to be questions
  if (trimmedText.length < 5) return false;
  
  // Simple question mark detection (most reliable)
  if (trimmedText.endsWith('?')) return true;
  
  // Common question starters
  const questionStarters = [
    'who', 'what', 'when', 'where', 'why', 'how', 'can you', 'could you',
    'would you', 'will you', 'do you', 'does', 'did', 'is', 'are', 'was',
    'were', 'have', 'has', 'should', 'could', 'would', 'may', 'might',
    'can i', 'should i', 'tell me', 'explain'
  ];
  
  const lowerText = trimmedText.toLowerCase();
  
  // Check for question starters at the beginning of the text
  for (const starter of questionStarters) {
    if (lowerText.startsWith(starter + ' ')) return true;
  }
  
  // Check for common question patterns within the text
  const questionPatterns = [
    / can you /i,
    / could you /i,
    / will you /i,
    / would you /i,
    / do you know /i,
    / have you /i,
    / are you /i,
    / tell me about /i,
    / explain /i
  ];
  
  for (const pattern of questionPatterns) {
    if (pattern.test(lowerText)) return true;
  }
  
  // If includeImplicit is true, check for additional patterns that suggest
  // knowledge gaps or implicit questions
  if (includeImplicit) {
    const implicitPatterns = [
      /I (was |am |)wonder(ing|ed) (if|what|when|where|why|how|who)/i,
      /^(not sure|unclear) (what|when|where|why|how|who)/i,
      /^(I'm|I am|I was) (curious|interested|not sure|wondering) (about|if|whether)/i,
      / need to know /i,
      / trying to understand /i,
      / looking for information /i,
      / help me understand /i,
      / any (ideas|thoughts|suggestions) /i,
      / what (would|do) you (suggest|recommend|think) /i,
      / should we /i,
      / want to understand /i,
      / seeking (help|advice|input) /i
    ];
    
    for (const pattern of implicitPatterns) {
      if (pattern.test(lowerText)) return true;
    }
  }
  
  return false;
}

/**
 * Extracts questions from a longer text
 * @param {string} text - The text to analyze
 * @param {boolean} includeImplicit - Whether to include implicit questions and knowledge gaps
 * @return {string[]} - Array of detected questions
 */
export function extractQuestions(text, includeImplicit = false) {
  if (!text || typeof text !== 'string') return [];
  
  // Clean up text - normalize spaces and ensure proper sentence breaks
  const cleanedText = text
    .replace(/([.?!])\s*([A-Z])/g, '$1 $2') // Ensure space after sentence terminators
    .replace(/\s+/g, ' ') // Normalize spaces
    .trim();
  
  // Use a more sophisticated regex that handles various punctuation and spacing
  const sentenceRegex = /[^.!?]+[.!?]+\s*/g;
  const matches = cleanedText.match(sentenceRegex) || [];
  
  // Add any remaining text that might not end with punctuation
  const lastPunctuationIndex = Math.max(
    cleanedText.lastIndexOf('.'),
    cleanedText.lastIndexOf('!'),
    cleanedText.lastIndexOf('?')
  );
  
  if (lastPunctuationIndex < cleanedText.length - 1) {
    const remainder = cleanedText.substring(lastPunctuationIndex + 1).trim();
    if (remainder.length > 0) {
      matches.push(remainder);
    }
  }
  
  // Process each sentence
  const questions = matches
    .map(s => s.trim())
    .filter(s => s.length > 0)
    .filter(s => detectQuestion(s, includeImplicit));
  
  // Special case: if we couldn't find any explicit questions but the input has a "?"
  // anywhere, try to extract question segments
  if (questions.length === 0 && text.includes('?')) {
    // Find segments around question marks
    const questionSegments = text.split('?')
      .map((segment, index, arr) => {
        // Don't add ? to the last segment if there's nothing after it
        if (index === arr.length - 1 && segment.trim() === '') return null;
        
        // Try to form a reasonable question segment by looking for the start of the question
        // (either beginning of text or after a period)
        const start = Math.max(0, segment.lastIndexOf('.') + 1);
        return segment.substring(start).trim() + '?';
      })
      .filter(s => s && s.trim().length > 5); // Filter out very short segments
    
    if (questionSegments.length > 0) {
      return questionSegments;
    }
  }
  
  return questions;
}

/**
 * Categorizes a question based on its content
 * @param {string} question - The question text to categorize
 * @return {string} - The question category
 */
export function categorizeQuestion(question) {
  if (!question || typeof question !== 'string') return 'general';
  
  const lowercaseQuestion = question.toLowerCase();
  
  // Technical questions
  if (lowercaseQuestion.match(/how (do|does|can) (I|we|you) (configure|setup|install|implement|integrate|deploy|build|compile|debug|fix|solve)/i) ||
      lowercaseQuestion.match(/(error|bug|issue|problem|fail|exception|crash)/i) ||
      lowercaseQuestion.match(/(code|function|method|api|interface|library|framework|plugin|component|module|dependency|version)/i)) {
    return 'technical';
  }
  
  // Business or product questions
  if (lowercaseQuestion.match(/(cost|price|pricing|billing|subscription|plan|payment|discount|offer)/i) ||
      lowercaseQuestion.match(/(roi|return on investment|profit|revenue|sales|conversion|customer|client|market|industry)/i) ||
      lowercaseQuestion.match(/(feature|roadmap|timeline|release|launch|product|service|solution|platform|tool|application)/i) ||
      lowercaseQuestion.match(/(compare|difference|versus|vs|alternative|competitor|similar)/i)) {
    return 'business';
  }
  
  // Process questions
  if (lowercaseQuestion.match(/(step|process|procedure|workflow|approach|strategy|method|practice|policy|guideline|standard)/i) ||
      lowercaseQuestion.match(/(how (do|does|should) (I|we|you) (handle|manage|organize|structure|plan|schedule|coordinate))/i) ||
      lowercaseQuestion.match(/(best (way|practice|approach|method) (to|for))/i)) {
    return 'process';
  }
  
  // Clarification questions
  if (lowercaseQuestion.match(/(what (do|does) (you|that) mean|clarify|explain|elaborate|details|specifics)/i) ||
      lowercaseQuestion.match(/(confused|unclear|don't understand|not sure|could you (explain|clarify))/i) ||
      lowercaseQuestion.match(/^(sorry|excuse me|pardon).*\?/i)) {
    return 'clarification';
  }
  
  // Decision questions
  if (lowercaseQuestion.match(/(should (I|we) (choose|select|pick|opt for|go with|use))/i) ||
      lowercaseQuestion.match(/(which (is|would be) (better|best|preferable|recommended|suggested|advised))/i) ||
      lowercaseQuestion.match(/(what (would|do) you (recommend|suggest|advise|think))/i) ||
      lowercaseQuestion.match(/(pros and cons|advantages|disadvantages|benefits|drawbacks)/i)) {
    return 'decision';
  }
  
  // Opinion questions
  if (lowercaseQuestion.match(/(what (do|are) you (think|feel|believe))/i) ||
      lowercaseQuestion.match(/(opinion|perspective|view|viewpoint|stance|position|judgment)/i) ||
      lowercaseQuestion.match(/(agree|disagree|concur)/i)) {
    return 'opinion';
  }
  
  // Fallback to general
  return 'general';
}

/**
 * Calculates a priority score for a question based on its content and context
 * @param {string} question - The question text
 * @param {string} speaker - The speaker who asked the question
 * @return {number} - Priority score (1-10, with 10 being highest priority)
 */
export function calculateQuestionPriority(question, speaker = '') {
  if (!question || typeof question !== 'string') return 5; // Default to medium priority
  
  let score = 5; // Start with medium priority
  const lowercaseQuestion = question.toLowerCase();
  
  // High priority indicators
  if (lowercaseQuestion.includes('urgent') || 
      lowercaseQuestion.includes('important') ||
      lowercaseQuestion.includes('critical') ||
      lowercaseQuestion.includes('asap') ||
      lowercaseQuestion.includes('emergency') ||
      lowercaseQuestion.includes('immediately') ||
      lowercaseQuestion.includes('crucial') ||
      lowercaseQuestion.match(/^(can|could) (you|someone|anybody) (please|)( help| assist)/i)) {
    score += 2;
  }
  
  // Decision-related indicators
  if (lowercaseQuestion.includes('decide') ||
      lowercaseQuestion.includes('decision') ||
      lowercaseQuestion.match(/should (we|i) (do|use|try|implement|consider)/i)) {
    score += 1;
  }
  
  // Problem indicators
  if (lowercaseQuestion.includes('problem') ||
      lowercaseQuestion.includes('issue') ||
      lowercaseQuestion.includes('error') ||
      lowercaseQuestion.includes('not working') ||
      lowercaseQuestion.includes('failed') ||
      lowercaseQuestion.includes('trouble')) {
    score += 1;
  }
  
  // Lower priority indicators
  if (lowercaseQuestion.includes('curious') ||
      lowercaseQuestion.includes('wondering') ||
      lowercaseQuestion.match(/^just (a|one) (quick|small|minor) question/i) ||
      lowercaseQuestion.match(/when you (have time|get a chance)/i)) {
    score -= 1;
  }
  
  // Question length factor
  if (question.length < 30) {
    score -= 1; // Shorter questions tend to be less complex
  } else if (question.length > 150) {
    score += 1; // Longer questions may need more attention
  }
  
  // Question complexity - questions with multiple parts might be more significant
  if ((question.match(/\?/g) || []).length > 1) {
    score += 1; // Multiple questions in one
  }
  
  // Speaker importance - could be customized based on organizational hierarchy
  if (speaker && (speaker.toLowerCase().includes('ceo') || 
                 speaker.toLowerCase().includes('director') ||
                 speaker.toLowerCase().includes('vp') ||
                 speaker.toLowerCase().includes('chief'))) {
    score += 2;
  }
  
  // Ensure score is within 1-10 range
  return Math.max(1, Math.min(10, Math.round(score)));
}
