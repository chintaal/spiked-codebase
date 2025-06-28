# Smart Sales Assistant API Documentation

## Overview

The Smart Sales Assistant API provides real-time analysis of conversation snippets during sales calls. It uses advanced AI models from OpenAI to analyze customer intent, detect questions, identify information gaps, suggest appropriate responses, and analyze sentiment.

## Base URL

```
https://your-api-domain.com
```

## Authentication

Authentication is required for all API endpoints. Use the following header in all requests:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### 1. Analyze Conversation

Analyzes a conversation snippet and returns intent, questions, information gaps, suggested responses, and sentiment analysis.

**URL**: `/analyze`

**Method**: `POST`

**Content-Type**: `application/json`

**Request Parameters**:

| Parameter           | Type    | Required | Description                                           |
|--------------------|---------|----------|-------------------------------------------------------|
| conversation       | string  | Yes      | A 15-20 word conversation snippet to analyze          |
| max_response_length| integer | No       | Maximum length of the generated response (default: 200)|
| tone               | string  | No       | Tone of the response (professional, friendly, assertive, etc.) |
| include_sources    | boolean | No       | Whether to include source documents in the response   |

**Example Request**:

```json
{
  "conversation": "I'm interested in your product, but I'm not sure if it's compatible with our existing systems. Can you tell me about your integration capabilities?",
  "max_response_length": 150,
  "tone": "professional",
  "include_sources": true
}
```

**Example Response**:

```json
{
  "intent": "product compatibility",
  "question": "Can you tell me about your integration capabilities?",
  "information_gap": "No specific details about their existing systems were provided.",
  "response": "Our platform offers seamless integration with all major EHR systems including Epic, Cerner, and Meditech through secure API connections. We also have pre-built connectors for most billing systems. I'd be happy to discuss your specific environment to show exactly how we could integrate.",
  "sentiment": "neutral",
  "meta": {
    "usage": {
      "completion_tokens": 112,
      "prompt_tokens": 845,
      "total_tokens": 957
    },
    "sources": [
      "Our platform integrates with the following EHR/EMR systems: Epic, Cerner, Meditech, Allscripts, NextGen, and others. Integration is done via secure API connections and follows all HIPAA compliance requirements.",
      "Our connector-based architecture allows for rapid deployment with minimal IT resources. Most integrations can be completed within 2-4 weeks."
    ]
  }
}
```

**Response Parameters**:

| Parameter       | Type    | Description                                          |
|----------------|---------|------------------------------------------------------|
| intent         | string  | Classification of the user's intent                   |
| question       | string  | Explicit or implied question detected in the conversation |
| information_gap| string  | Summary of missing or ambiguous information           |
| response       | string  | Generated, sales-friendly reply                       |
| sentiment      | string  | Sentiment classification (positive, neutral, negative)|
| meta           | object  | Additional metadata including token usage and sources |

**Status Codes**:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid input parameters
- `401 Unauthorized`: Invalid or missing API key
- `500 Internal Server Error`: Server error occurred

## Performance Considerations

- The API is optimized for low-latency responses, with a target of under 300ms per request.
- For best results, keep conversation snippets concise (15-20 words).
- Responses are cached for improved performance.

## Rate Limiting

The API is rate-limited to:
- 100 requests per minute
- 1,000 requests per hour
- 10,000 requests per day

Exceeding these limits will result in a `429 Too Many Requests` response.

## Support

For API support, please contact: support@your-company.com
