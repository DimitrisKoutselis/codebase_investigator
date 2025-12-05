# Codebase Investigator

A RAG (Retrieval-Augmented Generation) chatbot that ingests GitHub repositories and lets you ask questions about the code. Built with **MCP (Model Context Protocol)** as a central design pattern.

## Features

- **Ingest any GitHub repository** - Clone and index codebases automatically
- **Semantic code search** - Find relevant code using natural language queries
- **Conversational interface** - Chat about code with context-aware responses
- **MCP-powered tools** - Standardized tool protocol for LLM access
- **Real-time streaming** - WebSocket support for live responses
- **React Frontend** - Modern web UI for easy interaction

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Frontend | React + Vite + Tailwind CSS |
| AI Orchestration | LangGraph |
| LLM | Google Gemini |
| Vector Store | FAISS |
| Cache & Storage | Redis |
| Tool Protocol | MCP |
| Containerization | Docker |

## Quick Start with Docker (Recommended)

The easiest way to run Codebase Investigator is with Docker Compose. This bundles the backend (with Redis), and frontend together in containers.

### Prerequisites

- Docker and Docker Compose installed
- Google Gemini API key

### 1. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# At minimum, set GEMINI_API_KEY
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 3. Access the Application

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |

### Docker Commands

```bash
# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild after code changes
docker-compose up --build

# Remove volumes (clears all data)
docker-compose down -v
```

---

## Alternative: Local Development Setup

If you prefer to run without Docker for development:

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Redis server running locally
- Google Gemini API key

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/codebase-investigator.git
cd codebase-investigator

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys

# Start Redis (if not running)
# Windows: Use Redis for Windows or WSL
# Mac: brew services start redis
# Linux: sudo systemctl start redis

# Run the backend server
uvicorn src.presentation.main:app --reload
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access Points (Local Development)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |

---

## API Usage

### 1. Ingest a Repository

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'
```

Response:

```json
{
  "codebase_id": "abc123",
  "repo_url": "https://github.com/owner/repo",
  "status": "completed",
  "file_count": 42
}
```

### 2. Chat with the Codebase

```bash
curl -X POST http://localhost:8000/chat/{codebase_id}/{session_id} \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the main function do?"}'
```

Response:

```json
{
  "session_id": "uuid",
  "message": {
    "role": "assistant",
    "content": "The main function initializes...",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "sources": ["src/main.py"]
}
```

### 3. Stream Responses (WebSocket)

Connect to: `ws://localhost:8000/ws/chat/{codebase_id}/{session_id}`

Send:

```json
{"message": "Explain the authentication flow"}
```

Receive (streaming):

```json
{"type": "chunk", "content": "The authentication..."}
{"type": "chunk", "content": " flow starts with..."}
{"type": "done", "sources": ["src/auth.py"]}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest` | Ingest a GitHub repository |
| GET | `/ingest/{id}` | Get ingestion status |
| GET | `/ingest` | List all codebases |
| POST | `/chat/{codebase_id}/{session_id}` | Send a message |
| POST | `/chat/{codebase_id}/{session_id}/stream` | Stream a response (SSE) |
| WS | `/ws/chat/{codebase_id}/{session_id}` | WebSocket chat |
| GET | `/sessions/{id}` | Get session with history |
| GET | `/sessions/codebase/{id}` | List sessions for codebase |
| DELETE | `/sessions/{id}` | Delete a session |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `MISTRAL_API_KEY` | No | - | Mistral API key (alternative LLM) |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL |
| `LANGCHAIN_TRACING_V2` | No | `false` | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | No | - | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | `Codebase Investigator` | LangSmith project name |
| `GITHUB_TOKEN` | No | - | GitHub token for private repos |
| `DEBUG` | No | `false` | Debug mode |

## Architecture

This project follows **Clean Architecture** principles:

```text
src/
├── domain/           # Core business logic (no dependencies)
│   ├── entities/     # ChatSession, Codebase, Message
│   ├── value_objects/# RepoURL, SessionId, FilePath
│   ├── repositories/ # Abstract interfaces
│   └── exceptions/   # Domain errors
│
├── application/      # Use cases & DTOs
│   ├── use_cases/    # IngestCodebase, SendMessage, GetSession
│   ├── dtos/         # API data models
│   └── interfaces/   # Port interfaces (IGitService, IVectorStore, IMCPClient)
│
├── infrastructure/   # External implementations
│   ├── mcp/          # MCP servers & client (central focus)
│   ├── llm/          # LangGraph workflow & agents
│   ├── cache/        # Redis caching
│   ├── vector_store/ # FAISS embeddings
│   ├── git/          # Git operations
│   └── repositories/ # Redis implementations
│
├── presentation/     # API layer
│   ├── api/          # FastAPI routers & dependencies
│   ├── websocket/    # Real-time chat
│   └── main.py       # Application entry point
│
frontend/             # React frontend
├── src/
│   ├── api/          # API client
│   ├── components/   # React components
│   └── pages/        # Page components
├── Dockerfile        # Frontend container
└── nginx.conf        # Production server config
```

## MCP (Model Context Protocol)

MCP is the **central learning focus** of this project. It provides a standardized way for LLMs to access tools and resources.

### Our MCP Servers

#### CodebaseMCPServer

Exposes semantic code search tools:

| Tool | Description |
|------|-------------|
| `search_code` | Vector similarity search over codebase |
| `read_file` | Read specific file contents |
| `list_files` | List repository files |
| `get_repo_summary` | High-level repo overview |

#### FileMCPServer

Simple file system access:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `list_directory` | List directory contents |
| `search_files` | Glob pattern search |
| `grep` | Text pattern search in files |

### Using MCP Tools

```python
from src.infrastructure.mcp.client import MCPClientManager

client = MCPClientManager()
await client.connect("codebase")

# List available tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("search_code", {
    "query": "authentication",
    "top_k": 5
})
```

## How It Works

### Ingestion Flow

1. **Validate URL** - RepoURL value object validates GitHub URL format
2. **Clone Repository** - GitService clones repo with depth=1
3. **Parse Files** - Extract code from supported file types
4. **Generate Embeddings** - Create vector embeddings using Gemini
5. **Store in FAISS** - Index embeddings for similarity search
6. **Save Metadata** - Store codebase info in Redis

### Chat Flow

1. **Receive Query** - User sends natural language question
2. **Retrieve Context** - LangGraph retrieves relevant code via:
   - Direct FAISS vector search, or
   - MCP tools (search_code, read_file)
3. **Generate Response** - LLM generates answer with code context
4. **Return with Sources** - Response includes referenced file paths

## Development

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - AI agent orchestration
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [React](https://react.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
