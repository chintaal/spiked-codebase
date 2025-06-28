# Environment Setup Guide

This guide will help you set up your local development environment.

## Prerequisites

- Python 3.8 or higher
- OpenAI API account and API key

## Setup Steps

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Set up Python virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
# Backend environment
cp backend/.env.example backend/.env

# Frontend environment  
cp frontend/.env.example frontend/.env
```

Edit both `.env` files and add your OpenAI API key:
```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

For the frontend, use:
```
VITE_OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 5. Get your OpenAI API Key
1. Go to https://platform.openai.com/
2. Sign in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and paste it in your `.env` file

### 6. Run the application
```bash
# Start the backend server
cd backend
python -m uvicorn app.main:app --reload

# In another terminal, start the frontend (if applicable)
cd frontend
npm install
npm run dev
```

## Important Security Notes

- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env` file is already in `.gitignore` to prevent accidental commits
- Always use environment variables for sensitive configuration
- Regularly rotate your API keys for security

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `OPENAI_MODEL` | OpenAI model to use | No (defaults to gpt-4o) |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | No (defaults to text-embedding-3-large) |
| `EMBEDDING_DIMENSION` | Embedding dimension | No (defaults to 3072) |
| `KNOWLEDGE_DIR` | Knowledge base directory | No (defaults to knowledge) |
| `MAX_RESPONSE_LENGTH` | Maximum response length | No (defaults to 200) |
| `DEFAULT_TONE` | Default conversation tone | No (defaults to professional) |

## Troubleshooting

### Common Issues

1. **Missing API Key Error**
   - Ensure your `.env` file exists and contains `OPENAI_API_KEY`
   - Verify the API key is valid and has credits available

2. **Module Not Found Errors**
   - Ensure you're in the correct directory
   - Check that virtual environment is activated
   - Reinstall requirements: `pip install -r requirements.txt`

3. **Permission Errors**
   - On macOS/Linux, you might need to use `python3` instead of `python`
   - Ensure you have write permissions in the project directory
