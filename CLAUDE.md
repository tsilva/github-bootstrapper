# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Bootstrapper is a Python tool that syncs all GitHub repositories (public and private) for a user to their local machine. It handles cloning new repos and updating existing ones using the GitHub API, with support for both authenticated and unauthenticated modes.

## Development Setup

This project uses `uv` for dependency management. Install dependencies:
```bash
uv sync
```

Create a `.env` file (use `.env.example` as template):
```
GITHUB_USERNAME=your_github_username
REPOS_BASE_DIR=/path/to/your/repos/directory
GITHUB_TOKEN=your_github_token  # Optional but recommended
```

Run the tool:
```bash
uv run python main.py
```

Or install in development mode and run directly:
```bash
uv sync
uv run github-bootstrapper
```

## Architecture

### Entry Point
- `main.py`: Contains all core logic including GitHub API interactions, repository syncing, and orchestration

### Configuration
- `config.py`: Simple configuration class that validates environment variables (note: currently not used by main.py, which reads env vars directly)
- `.env`: Environment-based configuration for GitHub credentials and base directory

### Two Operating Modes

1. **Authenticated mode** (with GITHUB_TOKEN):
   - Uses `/user/repos` endpoint to get all accessible repos (private + public + org repos)
   - Enables parallel processing with ThreadPoolExecutor using CPU count as worker limit
   - Clones using SSH URLs (`ssh_url` field)

2. **Unauthenticated mode** (without GITHUB_TOKEN):
   - Uses `/users/{username}/repos` endpoint for public repos only
   - Fetches organization repos separately via `/users/{username}/orgs` and `/orgs/{org}/repos`
   - Sequential processing only
   - Uses HTTPS clone URLs (`clone_url` field)

### Key Functions

- `get_repos()`: Main API orchestration, handles pagination and deduplication
- `sync_repo()`: Core sync logic - clones new repos or pulls updates for existing ones
- `has_unstaged_changes()`: Safety check that prevents updates to dirty working directories
- `process_repo()`: Wrapper that logs repo details and calls sync_repo()
- `get_clone_url()`: Returns SSH URL when token available, HTTPS otherwise

### Logging

- Timestamped log files created in `logs/` directory
- Format: `github_sync_YYYYMMDD_HHMMSS.log`
- Dual output to both file and console

## Important Implementation Details

- Repositories with unstaged changes are skipped during updates to prevent data loss
- GitHub API pagination handled with 100 items per page
- Repository deduplication by ID to handle overlaps between user/org repos
- Default branch detection before pulling (uses `git rev-parse --abbrev-ref HEAD`)
- Rate limit detection with graceful exit on HTTP 403
- Thread-safe parallel processing when token is available

## Key Dependencies

- `requests`: GitHub API interaction
- `python-dotenv`: Environment variable management
- `PyGithub`: Currently installed but not used in code (consider removing or utilizing)

## Important Note

README.md must be kept up to date with any significant project changes.
