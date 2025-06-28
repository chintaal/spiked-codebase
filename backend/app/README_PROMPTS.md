# Prompts Directory

This file contains all centralized prompts used throughout the sales assistant application.

## Available Prompts

### ENHANCED_RAG_SYSTEM_PROMPT
Used by the enhanced RAG pipeline for generating structured responses with various components like straightforward answers, statistics, comparisons, etc.

### OPENAI_CLIENT_SYSTEM_PROMPT  
Used by the OpenAI client for conversation analysis with exactly 8-10 statistics and sales points.

### DOCUMENT_PROCESSING_SYSTEM_PROMPT
Used for document processing and extraction tasks.

### TRANSCRIPTION_SYSTEM_PROMPT
System prompt for transcription formatting tasks.

### TRANSCRIPTION_FORMATTING_PROMPT
Template for formatting and cleaning up transcripts with context and action type parameters.

## Usage

Import the prompts you need:

```python
from app.prompts import ENHANCED_RAG_SYSTEM_PROMPT, OPENAI_CLIENT_SYSTEM_PROMPT

# Use with formatting
system_message = ENHANCED_RAG_SYSTEM_PROMPT.format(tone="professional")
```

## Adding New Prompts

When adding new prompts:
1. Add the prompt constant to this file
2. Update imports in files that need it
3. Update this README documentation
