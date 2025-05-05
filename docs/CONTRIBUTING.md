# Contributing to Grocy Recipe Assistant

Thank you for your interest in contributing to the Grocy Recipe Assistant project! This document provides guidelines and instructions for setting up your development environment and contributing to the codebase.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Git
- A Grocy instance (or you can use the mock data for development)
- Spoonacular API key (free tier is sufficient for development)
- OpenAI API key (for AI features)

### Setting Up Your Development Environment

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/grocy-recipe-assistant.git
   cd grocy-recipe-assistant
   ```

2. **Create your environment file**

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file to include your API keys and configuration.

3. **Start the development environment**

   ```bash
   docker-compose up -d
   ```

   This will start PostgreSQL, Redis, and the FastAPI backend.

4. **Run tests to verify setup**

   ```bash
   docker-compose exec backend pytest
   ```

## Development Workflow

### Branch Strategy

- `main` - Stable production-ready code
- `dev` - Development branch for integrating features
- `feature/*` - Feature branches for new work
- `fix/*` - Branches for bug fixes

### Making Changes

1. Create a new branch from `dev`:
   ```bash
   git checkout dev
   git pull
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with meaningful messages:
   ```bash
   git commit -m "Add feature: detailed description of what was added"
   ```

3. Push your branch to GitHub:
   ```bash
   git push -u origin feature/your-feature-name
   ```

4. Create a pull request against the `dev` branch.

### Code Style Guidelines

- Follow Python PEP 8 style guide
- Use type hints for function parameters and return values
- Document your code with docstrings
- Run `pylint` on your code before submitting a PR

```bash
docker-compose exec backend pylint backend/app
```

#### Linting Configuration

The project uses a customized `.pylintrc` file at the root directory to enforce consistent code style and quality:

- Set `max-line-length=100` to allow reasonable line lengths
- Disabled certain warnings common in Docker projects (import-error, no-name-in-module)
- Set `max-module-lines=1200` to accommodate larger modules like recipes.py
- Enhanced import order checking (standard library first, then third-party, then application imports)
- Use `%` formatting in logging statements rather than f-strings for better performance

You can run Black to automatically fix most formatting issues:

```bash
# Install Black if not already installed
pip install black

# Run Black on Python files
black backend/app/recipes.py
```

Common linting fixes:
1. Use proper import order (standard library → third-party → application)
2. Convert f-string logging to % formatting: `logger.info("Found %d items", count)` 
3. Fix trailing whitespace and line length with Black
4. Add type hints for function parameters and return values

### Testing

- Add tests for any new functionality
- Ensure existing tests pass with your changes
- Mock external API calls in tests

```bash
docker-compose exec backend pytest
```

## Architecture Overview

Before contributing, please familiarize yourself with the project architecture:

1. **FastAPI Backend**: Handles API requests and orchestrates the various services
2. **PostgreSQL Database**: Stores user preferences, ratings, and inventory
3. **Redis Cache**: Caches API responses and AI operations
4. **OpenAI Integration**: Handles AI classification and review parsing
5. **Spoonacular Integration**: Sources recipes and taste profiles

Refer to [[SYSTEM_OVERVIEW]] for detailed architectural documentation.

## Documentation

- Update documentation when adding features or making significant changes
- Keep API examples up to date in [[API_REFERENCE]]
- Document any new environment variables or configuration options

## Submitting a PR

1. Ensure your code passes all tests
2. Update relevant documentation
3. Fill in the PR template with:
   - Description of changes
   - Related issue numbers
   - Screenshots for UI changes
   - Any breaking changes

## Getting Help

If you have questions while contributing:

- Open an issue on GitHub for technical questions
- Reference existing documentation in the `/docs` directory

Thank you for contributing to the Grocy Recipe Assistant project!
