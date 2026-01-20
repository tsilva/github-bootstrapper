# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Bootstrapper is a multi-operation repository management system that performs bulk operations on GitHub repositories. It supports seven operations: sync (clone + pull), clone-only, pull-only, status (synchronization status reporting), readme-gen (README generation via Claude), settings-clean (Claude Code settings cleanup), and sandbox-enable (enable Claude Code sandbox mode). Features include parallel processing, flexible filtering, and an extensible operation framework.

## Development Setup

This project uses `uv` for dependency management.

**For local development:**
```bash
uv sync
```

**For global installation:**
```bash
uv tool install .
```

Create a `.env` file (use `.env.example` as template):
```
GITHUB_USERNAME=your_github_username
REPOS_BASE_DIR=/path/to/your/repos/directory  # Defaults to current directory
GITHUB_TOKEN=your_github_token  # Optional but recommended
```

Run operations (examples use global installation; for local dev, prefix with `uv run`):
```bash
# Check repository status
github-bootstrapper status --username your-username

# Sync all repositories
github-bootstrapper sync --username your-username

# Clone only missing repositories
github-bootstrapper clone-only --username your-username --dry-run

# Pull updates for existing repositories
github-bootstrapper pull-only --username your-username

# Generate READMEs
github-bootstrapper readme-gen --username your-username --exclude-forks

# Enable sandbox mode
github-bootstrapper sandbox-enable --username your-username

# Clean Claude settings
github-bootstrapper settings-clean --username your-username --mode analyze
```

## Architecture

### Project Structure

```
github-bootstrapper/
├── github_bootstrapper/             # Core package
│   ├── __main__.py                 # CLI entry point with argparse
│   ├── config.py                   # Configuration management
│   ├── core/
│   │   ├── github_client.py        # GitHub API client
│   │   ├── repo_manager.py         # Operation orchestrator
│   │   └── logger.py               # Logging utilities
│   ├── operations/
│   │   ├── base.py                 # Abstract Operation class
│   │   ├── registry.py             # Auto-discovery via introspection
│   │   ├── sync.py                 # Clone + pull operation
│   │   ├── clone_only.py           # Clone-only operation
│   │   ├── pull_only.py            # Pull-only operation
│   │   ├── status.py               # Repository status operation
│   │   ├── readme_gen.py           # README generation via Claude CLI
│   │   ├── settings_clean.py       # Settings cleanup via script
│   │   └── sandbox_enable.py       # Sandbox mode enablement
│   └── utils/
│       ├── git.py                  # Git helpers
│       ├── progress.py             # Progress tracking
│       └── filters.py              # Repository filtering
├── pyproject.toml                  # Package configuration
└── uv.lock                         # Dependency lock file
```

### Operation Framework

**Strategy Pattern with Auto-Discovery:**
- `Operation` base class defines interface: `execute()`, `should_skip()`, hooks
- Each operation is self-contained, isolated, and testable
- `OperationRegistry` auto-discovers operations via Python introspection
- `RepoManager` orchestrates parallel/sequential execution

**Adding New Operations:**
1. Create file in `operations/` directory
2. Inherit from `Operation` base class
3. Implement `execute()` method
4. Set class attributes: `name`, `description`, `requires_token`, `safe_parallel`
5. Registry auto-discovers it - no other changes needed!

### Core Components

**GitHubClient** (`core/github_client.py`):
- GitHub API interactions with pagination
- Authenticated mode: `/user/repos` endpoint (all repos including private)
- Unauthenticated mode: `/users/{username}/repos` + org repos
- Clone URL selection: SSH when authenticated, HTTPS otherwise

**RepoManager** (`core/repo_manager.py`):
- Orchestrates operation execution
- Parallel execution with ThreadPoolExecutor (authenticated mode)
- Sequential execution (unauthenticated or non-thread-safe operations)
- Exception handling and result collection

**RepoFilter** (`utils/filters.py`):
- Filter by: repo names, orgs, patterns (glob), visibility, fork/archived status
- Supports multiple criteria with AND logic

### Configuration

- `Config` class merges .env and CLI arguments
- CLI arguments override environment variables
- Required: `GITHUB_USERNAME`, `REPOS_BASE_DIR`
- Optional: `GITHUB_TOKEN` (enables auth mode and parallelization)

### Logging

- Operation-specific log files: `logs/github_{operation}_YYYYMMDD_HHMMSS.log`
- Dual output to both file and console
- Progress tracking with live updates: `[████████░░] 80% (40/50) ✓35 ⊘3 ✗2`

## Operations Overview

1. **sync** - Clone new repos + pull existing (default behavior)
   - Parallelization: Yes (thread-safe)
   - Skips repos with unstaged changes

2. **clone-only** - Only clone repos not yet cloned
   - Parallelization: Yes (thread-safe)
   - Skips existing repos

3. **pull-only** - Only pull updates for existing repos
   - Parallelization: Yes (thread-safe)
   - Skips repos with unstaged changes

4. **status** - Report repository synchronization status
   - Parallelization: Yes (read-only operation)
   - Categorizes repos: In sync, Unpushed changes, Unpulled changes, Diverged, Uncommitted changes, Not cloned
   - Fetches from remote to ensure accurate status
   - Provides grouped summary output

5. **readme-gen** - Generate/update README.md using Claude's readme-generator skill
   - Parallelization: No (Claude API rate limits)
   - Invokes Claude CLI: `claude -p "prompt" --permission-mode acceptEdits`
   - Skips archived and fork repos by default
   - Timeout: 5 minutes per repo

6. **settings-clean** - Analyze/clean Claude Code settings
   - Parallelization: Yes (isolated settings files)
   - Invokes settings-cleaner script via `uv run`
   - Modes: analyze (default), clean, auto-fix
   - Skips repos without `.claude/settings.local.json`

7. **sandbox-enable** - Enable Claude Code sandbox mode
   - Parallelization: Yes (isolated JSON files)
   - Direct JSON manipulation
   - Sets: `{"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true}}`

## Important Implementation Details

- Repositories with unstaged changes are skipped during pull operations to prevent data loss
- GitHub API pagination handled with 100 items per page
- Repository deduplication by ID to handle overlaps between user/org repos
- Default branch detection before pulling (uses `git rev-parse --abbrev-ref HEAD`)
- Rate limit detection with graceful exit on HTTP 403
- Thread-safe parallel processing when token is available and operation allows it
- Dry-run mode available for all operations
- Comprehensive filtering: by repo name, org, pattern, visibility, fork/archived status

## Key Dependencies

- `requests`: GitHub API interaction
- `python-dotenv`: Environment variable management
- `PyGithub`: Currently installed but not used in code (consider removing or utilizing)

## Important Note

README.md must be kept up to date with any significant project changes.
