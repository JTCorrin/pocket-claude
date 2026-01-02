# Pocket Claude

A mobile-first application that brings Claude AI to your pocket, enabling you to run Claude Code sessions on your own infrastructure with full git repository integration.

## 📱 What is Pocket Claude?

Pocket Claude is a cross-platform mobile application (iOS/Android) that connects to a self-hosted backend running Claude Code CLI. This architecture enables:

- **Private AI Development**: Run Claude on your own VM or local machine with full control over your data
- **Git Repository Integration**: Connect your GitHub, GitLab, or Gitea repositories with secure OAuth 2.0 authentication
- **Mobile-First Experience**: Chat with Claude, manage sessions, and review code changes from your mobile device
- **Offline Support**: Request queuing and response caching for seamless offline/online transitions
- **Real-time Collaboration**: Stream responses and track long-running tasks asynchronously

## 🏗️ Architecture

This is a monorepo containing two applications:

```
pocket-claude/
├── app/          # Mobile frontend (SvelteKit + Capacitor)
├── api/          # Backend API (FastAPI + Claude Code CLI)
└── docs/         # Documentation
```

### Frontend (`/app`)
- **Framework**: SvelteKit 2 with Svelte 5 (runes)
- **Mobile**: Capacitor 8 for iOS and Android
- **Styling**: Tailwind CSS 4 + shadcn-svelte components
- **State**: Svelte 5 runes (`$state`, `$derived`, `$effect`)
- **Validation**: Zod 4 for type-safe API contracts
- **Testing**: Vitest + Playwright

### Backend (`/api`)
- **Framework**: FastAPI with async support
- **CLI Integration**: Claude Code CLI wrapper
- **Architecture**: Clean architecture (routes → controllers → services)
- **Validation**: Pydantic 2 models
- **Testing**: pytest + pytest-asyncio

## ✨ Features

### Current Features
- **Chat Interface**: Conversational UI for interacting with Claude Code
- **Session Management**: Create, resume, and list Claude Code sessions
- **Async Task Queue**: Handle long-running Claude operations without blocking
- **Git OAuth Integration**: Secure PKCE-based OAuth for GitHub, GitLab, and Gitea
- **API Configuration**: Runtime configuration of backend URL without rebuilding
- **Offline Mode**: Request queuing and automatic retry with connectivity monitoring
- **Type Safety**: End-to-end type safety with Zod schemas and Pydantic models

### In Development
- Git operations (clone, commit, push, PR creation)
- Session persistence and history
- File attachments and image uploads
- Real-time streaming responses
- Dark mode support

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ and **pnpm** 8+
- **Python** 3.13+
- **uv** (Python package manager)
- **Claude Code CLI** installed and configured
- **(Optional)** Xcode for iOS development
- **(Optional)** Android Studio for Android development

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/JTCorrin/pocket-claude.git
cd pocket-claude
```

#### 2. Backend Setup

```bash
cd api

# Install dependencies
uv sync

# Create .env file
cat > .env << EOF
# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Pocket Claude API
VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true

# CORS (adjust for production)
CORS_ORIGINS=["http://localhost:5173", "capacitor://localhost"]

# Git OAuth (optional - see docs/GIT_OAUTH_SETUP.md)
GITHUB_CLIENT_ID=your_github_client_id_here
GITLAB_CLIENT_ID=your_gitlab_client_id_here
GITEA_CLIENT_ID=your_gitea_client_id_here
EOF

# Run the API
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. API documentation is auto-generated at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 3. Frontend Setup

```bash
cd app

# Install dependencies
pnpm install

# Create .env file
cat > .env << EOF
VITE_API_URL=http://localhost:8000
EOF

# Run development server
pnpm dev
```

The app will be available at `http://localhost:5173`.

#### 4. Mobile Development (Optional)

For iOS/Android development, you'll need to sync the Capacitor projects:

```bash
cd app

# Build the web app
pnpm build

# Sync to Capacitor
pnpm sync

# Open in Xcode (iOS)
pnpm open:ios

# Open in Android Studio (Android)
pnpm open:android
```

## 🔐 Git OAuth Setup

To connect git repositories, you need to register OAuth applications with your git providers and configure the client IDs.

**📖 See detailed setup guide**: [docs/GIT_OAUTH_SETUP.md](docs/GIT_OAUTH_SETUP.md)

The guide covers:
- Creating OAuth apps for GitHub, GitLab, and Gitea
- PKCE flow explanation and security benefits
- Capacitor configuration for deep links
- Production deployment recommendations
- Troubleshooting common OAuth issues

### Quick Start

1. Register OAuth app with your provider (see guide for details)
2. Add client ID to `api/.env`:
   ```bash
   GITHUB_CLIENT_ID=your_client_id_here
   ```
3. Configure redirect URI in OAuth app: `pocketclaude://oauth-callback`
4. Connect via Settings page in the mobile app

## 🧪 Testing

### Frontend Tests

```bash
cd app

# Run all tests
pnpm test

# Run client tests only (browser/Playwright)
pnpm test -- --run --project=client

# Run server tests only (Node)
pnpm test -- --run --project=server

# Type checking
pnpm check

# Linting
pnpm lint
```

### Backend Tests

```bash
cd api

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_git_service.py -v
```

## 📁 Project Structure

```
pocket-claude/
├── app/                          # Frontend application
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/             # API client and endpoints
│   │   │   │   ├── client.ts    # HTTP client with auth
│   │   │   │   ├── endpoints/   # Type-safe API wrappers
│   │   │   │   └── index.ts     # API exports
│   │   │   └── components/      # Reusable components
│   │   └── routes/              # SvelteKit routes
│   │       ├── chat/            # Chat interface
│   │       ├── settings/        # Settings & OAuth
│   │       └── +layout.svelte   # Root layout
│   ├── android/                 # Android Capacitor project
│   ├── ios/                     # iOS Capacitor project
│   └── package.json
│
├── api/                         # Backend API
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── core/
│   │   │   ├── config.py        # Settings/environment
│   │   │   └── exceptions.py   # Custom exceptions
│   │   ├── api/v1/
│   │   │   ├── routes/          # API endpoints
│   │   │   └── controllers/     # Business logic
│   │   ├── services/            # Core services
│   │   │   ├── claude_service.py
│   │   │   ├── git_service.py
│   │   │   └── task_service.py
│   │   └── models/              # Pydantic models
│   └── tests/
│
└── docs/                        # Documentation
    ├── GIT_OAUTH_SETUP.md       # OAuth configuration guide
    └── CLAUDE.md                # Development instructions
```

## 🔧 Development

### Frontend Commands

```bash
cd app
pnpm dev          # Dev server (localhost:5173)
pnpm build        # Production build
pnpm check        # TypeScript type checking
pnpm lint         # Prettier + ESLint
pnpm test         # Run all tests
pnpm sync         # Sync to Capacitor
pnpm open:ios     # Open Xcode
pnpm open:android # Open Android Studio
```

### Backend Commands

```bash
cd api
uv sync                                              # Install dependencies
python -m uvicorn app.main:app --reload --port 8000  # Dev server
pytest                                               # Run tests
pytest -v                                            # Verbose tests
```

### Docker (Backend)

```bash
cd api
docker build -t pocket-claude-api:latest .
docker run -p 8000:8000 pocket-claude-api:latest
```

## 🌐 Environment Variables

### Frontend (`.env`)

```bash
VITE_API_URL=http://localhost:8000  # Backend API base URL
```

Note: Users can override this at runtime via the Settings page without rebuilding.

### Backend (`.env`)

```bash
# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Pocket Claude API
VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true

# CORS Origins (comma-separated)
CORS_ORIGINS=["http://localhost:5173", "capacitor://localhost"]

# Git OAuth Client IDs (optional)
GITHUB_CLIENT_ID=
GITLAB_CLIENT_ID=
GITEA_CLIENT_ID=
```

## 🚢 Deployment

### Production Considerations

1. **Backend**:
   - Set `ENVIRONMENT=production` and `DEBUG=false`
   - Use HTTPS for all API endpoints
   - Implement database storage for OAuth tokens (currently in-memory)
   - Enable token encryption for git connections
   - Configure proper CORS origins
   - Set up monitoring and logging

2. **Frontend**:
   - Build production bundle: `pnpm build`
   - Configure production API URL in Settings or via `VITE_API_URL`
   - Register OAuth apps with production redirect URIs
   - Build and sign mobile apps for App Store/Play Store

3. **Security**:
   - Use HTTPS everywhere
   - Implement rate limiting
   - Enable OAuth token refresh
   - Encrypt sensitive data at rest
   - Regular security audits

## 📝 API Documentation

The API is fully documented with OpenAPI/Swagger. When the backend is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Key endpoints:

- `POST /api/v1/chat` - Send message to Claude
- `GET /api/v1/sessions` - List Claude sessions
- `POST /api/v1/git/oauth/initiate` - Start OAuth flow
- `POST /api/v1/git/oauth/callback` - Complete OAuth flow
- `GET /api/v1/git/connections` - List git connections
- `GET /api/v1/tasks/{task_id}` - Check async task status

## 🛠️ Tech Stack

| Component | Frontend | Backend |
|-----------|----------|---------|
| Framework | SvelteKit 2 (Svelte 5) | FastAPI |
| Language | TypeScript | Python 3.13+ |
| Validation | Zod 4 | Pydantic 2 |
| Testing | Vitest + Playwright | pytest + pytest-asyncio |
| Styling | Tailwind CSS 4 | - |
| Mobile | Capacitor 8 | - |
| Package Manager | pnpm | uv |

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with clear commit messages
4. Ensure all tests pass (`pnpm test` and `pytest`)
5. Run linters (`pnpm lint` and type checks)
6. Submit a pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Built with [Claude Code CLI](https://claude.ai/code)
- UI components from [shadcn-svelte](https://www.shadcn-svelte.com/)
- Mobile framework by [Capacitor](https://capacitorjs.com/)

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review API docs at `/docs` endpoint

---

**Note**: This project is under active development. OAuth token storage is currently in-memory (development only). Production deployments require database-backed token storage with encryption. See [docs/GIT_OAUTH_SETUP.md](docs/GIT_OAUTH_SETUP.md) for details.
