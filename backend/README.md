# Smart Sales Assistant API

A real-time, FastAPI-based smart sales assistant AI agent using the OpenAI API for sales conversation analysis and augmentation.

## Features

- **Real-time Conversation Analysis**: Analyze snippets of customer conversations to determine intent, detect questions, identify information gaps, and provide sentiment analysis.
- **Sales Response Generation**: Generate contextually relevant, sales-friendly responses using Retrieval-Augmented Generation (RAG).
- **Context-Aware Recommendations**: Leverage knowledge from battle cards, pricing documents, and other sales collateral to generate informed responses.
- **Batch Prompt Caching**: Zero-latency responses using batch-populated cache with actual `/analyze` endpoint responses (< 10ms response time).
- **Efficient Performance**: Asynchronous processing, intelligent caching, and optimized vector search for low-latency responses.

## Technical Stack

- **FastAPI**: For building high-performance async API endpoints
- **OpenAI**: For AI/ML functionalities (embeddings, chat completions, sentiment analysis)
- **FAISS/Chroma**: For efficient vector similarity search
- **Pydantic**: For input/output validation and schema definition

## Important Note on OpenAI API Usage

This application uses the OpenAI Python SDK. If you encounter the following error when running the application:

```
Error getting embedding: object CreateEmbeddingResponse can't be used in 'await' expression
```

This error occurs because the newer versions of the OpenAI Python SDK (v1.0.0 and above) changed how async/await works. The API calls should not be directly awaited. The code has been updated to fix this issue.

If you're using an older version of OpenAI SDK (v0.x.x), you may need to modify the code to use awaitable methods.

## Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/sales-assistant-api.git
   cd sales-assistant-api
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o
   OPENAI_EMBEDDING_MODEL=text-embedding-3-large
   EMBEDDING_DIMENSION=3072
   KNOWLEDGE_DIR=knowledge
   MAX_RESPONSE_LENGTH=200
   DEFAULT_TONE=professional
   ```

5. **Prepare knowledge documents**:
   Place your sales documents (battle cards, pricing sheets, etc.) in the `knowledge` directory. Documents should be processed into text format with `_processed.txt` suffix.

6. **Vector Database Management**:
   The application will automatically create and maintain a persistent vector database for your knowledge documents. When you start the application for the first time, it will create embeddings for all documents in the `knowledge` directory. These embeddings are stored on disk in the `vector_db` directory.

   - If you update your knowledge documents, you can rebuild the vector database without restarting the server by making a POST request to `/api/vector-db/rebuild`.
   - You can also use the management script:
     ```bash
     # Check the status of the vector database
     python scripts/manage_vector_db.py status
     
     # Rebuild the vector database
     python scripts/manage_vector_db.py rebuild
     
     # Clear the vector database (forcing a rebuild on next start)
     python scripts/manage_vector_db.py clear
     ```

7. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### `/analyze` - Conversation Analysis

**Method**: `POST`

**Purpose**: Analyze a conversation snippet and provide intent, questions, information gaps, a suggested response, and sentiment analysis.

**Request Parameters**:
- `conversation`: The conversation snippet to analyze (15-20 words recommended)
- `max_response_length`: Maximum length of the generated response (default: 200)
- `tone`: Tone of the response (professional, friendly, assertive, etc.)
- `include_sources`: Whether to include sources in the response

**Example Request**:
```json
{
  "conversation": "I'm interested in your product but I'm worried about the pricing. Is there a discount for yearly subscriptions?",
  "max_response_length": 150,
  "tone": "professional"
}
```

**Example Response**:
```json
{
  "intent": "pricing inquiry",
  "question": "Is there a discount for yearly subscriptions?",
  "information_gap": "No specific pricing details have been shared yet.",
  "response": "Yes, we offer a 20% discount on annual subscriptions compared to monthly billing. For healthcare organizations, we also have volume-based pricing tiers that can provide additional savings. Would you like me to share our pricing sheet which outlines these options in detail?",
  "sentiment": "neutral",
  "meta": {
    "usage": {
      "completion_tokens": 112,
      "prompt_tokens": 845,
      "total_tokens": 957
    }
  }
}
```

### Additional Endpoints

- **`/health`**: Check API status and service health
- **`/api/cache/stats`**: View batch cache statistics
- **`/api/cache/clear`**: Clear the batch cache
- **`/api/cache/batch-refresh`**: Populate cache with canonical questions via `/analyze` endpoint
- **`/api/cache/canonical-questions`**: List canonical questions used for batch caching
- **`/api/vector-db/rebuild`**: Rebuild the vector database when knowledge documents change

## Batch Prompt Caching System

The HealthAssist Batch Caching system provides **zero-latency responses** by pre-populating the cache with actual `/analyze` endpoint responses:

### Key Features
- **< 10ms response time** for cached questions
- **Intelligent similarity matching** using embeddings for question variations  
- **Batch population** with actual `/analyze` endpoint responses
- **Canonical questions** from `docs/questions_preprocessed`
- **Automatic fallback** to full RAG pipeline for new questions
- **Production-grade responses** (same quality as live `/analyze` calls)

### Performance Benefits
```
Cached Questions:     5-10ms   (98% faster)
Similar Questions:   15-25ms   (95% faster) 
New Questions:      300-500ms  (unchanged)
```

### Setting Up Batch Cache
```bash
# Populate cache with canonical questions
curl -X POST http://localhost:8000/api/cache/batch-refresh

# Check cache statistics
curl http://localhost:8000/api/cache/stats

# List canonical questions
curl http://localhost:8000/api/cache/canonical-questions
```

For detailed information, see [docs/BATCH_CACHING.md](docs/BATCH_CACHING.md).

## Performance Optimization

The API is optimized for ultra-low-latency responses through:

1. **Batch Prompt Caching**: Zero-latency responses for canonical questions using pre-populated cache
2. **Intelligent Question Matching**: Embedding-based semantic similarity for question variations
3. **Efficient Vector Search**: Using FAISS for high-performance similarity search
4. **Persistent Vector Database**: Embeddings are stored on disk and only recalculated when documents change
5. **Asynchronous Processing**: Utilizing FastAPI's async capabilities for non-blocking operations
6. **Chunked Document Storage**: Optimized document chunking for relevant context retrieval

## License

[MIT License](LICENSE)
