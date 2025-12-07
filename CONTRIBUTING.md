# Contributing to Wingman

Thank you for your interest in contributing to Wingman! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/wingman.git`
3. Add upstream remote: `git remote add upstream https://github.com/echohello-dev/wingman.git`

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/echohello-dev/wingman.git
cd wingman

# Copy environment file
cp .env.example .env

# Install dependencies
mise run install

# Start services
mise run up
```

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run backend
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Build
npm run build
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-slack-reactions`
- `fix/database-connection-issue`
- `docs/update-setup-guide`

### Commit Messages

Follow conventional commits:
```
feat: add reaction-based feedback
fix: resolve database connection timeout
docs: update SETUP.md with new instructions
test: add tests for RAG engine
refactor: simplify vector store initialization
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Write/update tests
4. Update documentation if needed
5. Run tests and linting
6. Submit a pull request

## Testing

### Backend Tests

```bash
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_api.py -v
```

### Frontend Tests

```bash
cd frontend
npm test

# With coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

### Integration Tests

```bash
# Start all services
mise run up

# Run integration tests
mise run test
```

## Style Guidelines

### Python (Backend)

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for functions and classes

```python
def generate_response(question: str, channel_id: str = None) -> Dict[str, Any]:
    """
    Generate a response using RAG
    
    Args:
        question: The user's question
        channel_id: Optional channel ID to filter context
        
    Returns:
        Dictionary with response and metadata
    """
    pass
```

### TypeScript (Frontend)

- Follow ESLint configuration
- Use TypeScript strict mode
- Prefer functional components
- Use meaningful variable names

```typescript
interface QuestionResponse {
  answer: string
  sources: Array<Record<string, any>>
  confidence: string
}

export async function askQuestion(
  question: string,
  channelId?: string
): Promise<QuestionResponse> {
  // Implementation
}
```

### Documentation

- Use Markdown format
- Include code examples
- Keep language clear and concise
- Update docs with code changes

## Project Structure

```
wingman/
├── backend/              # Python backend
│   ├── app/
│   │   ├── main.py      # FastAPI app
│   │   ├── slack_bot.py # Slack integration
│   │   ├── rag.py       # RAG engine
│   │   └── ...
│   └── tests/           # Backend tests
├── frontend/            # Next.js frontend
│   ├── app/            # Next.js app directory
│   ├── components/     # React components
│   ├── lib/            # Utilities
│   └── ...
├── docs/               # Documentation
└── docker compose.yml  # Docker setup
```

## Common Tasks

### Adding a New API Endpoint

1. Add route in `backend/app/main.py`
2. Add request/response models
3. Implement handler function
4. Add tests in `backend/tests/`
5. Update API documentation

### Adding a New Slack Event

1. Add handler in `backend/app/slack_bot.py`
2. Register event in `_register_handlers`
3. Update Slack app event subscriptions
4. Add tests

### Adding a Frontend Component

1. Create component in `frontend/components/`
2. Add TypeScript types
3. Import and use in pages
4. Add styling with Tailwind
5. Add tests if applicable

## Debugging

### Backend Debugging

```bash
# View logs
mise run logs-backend

# Access container
mise run shell-backend

# Check database
mise run shell-db
```

### Frontend Debugging

```bash
# View logs
mise run logs-frontend

# Run with verbose logging
cd frontend
npm run dev -- --verbose
```

## Getting Help

- Open an issue for bugs
- Start a discussion for questions
- Check existing issues/PRs first
- Provide detailed information

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make Wingman better for everyone. Thank you for taking the time to contribute! 🙏
