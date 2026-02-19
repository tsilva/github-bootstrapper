# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gitfleet is a multi-operation repository management system that performs bulk operations on GitHub repositories using a composable pipeline architecture. It supports eight pipelines: sync (clone + pull), clone-only, pull-only, status (synchronization status reporting), claude-exec (execute Claude prompts), settings-clean (Claude Code settings cleanup), sandbox-enable (enable Claude Code sandbox mode), and description-sync (sync GitHub repo description with README tagline). Features include parallel processing, flexible filtering, and an extensible pipeline framework.

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
GITHUB_TOKEN=your_github_token  # Optional but recommended
```

**Important:** Always run from the directory containing your repositories.

Run pipelines (examples use global installation; for local dev, prefix with `uv run`):
```bash
# Check repository status
gitfleet status --username your-username

# Sync all repositories
gitfleet sync --username your-username

# Clone only missing repositories
gitfleet clone-only --username your-username --dry-run

# Pull updates for existing repositories
gitfleet pull-only --username your-username

# List available pipelines
gitfleet --list-pipelines

# Execute Claude prompts (raw prompts or skills)
gitfleet claude-exec "Add a LICENSE file" --username your-username
gitfleet claude-exec "/readme-generator" --repo my-repo

# Enable sandbox mode
gitfleet sandbox-enable --username your-username

# Clean Claude settings
gitfleet settings-clean --username your-username --mode analyze

# Sync repo descriptions with README taglines
gitfleet description-sync --username your-username --dry-run
```

## Architecture

### Project Structure

```
gitfleet/
├── gitfleet/             # Core package
│   ├── __main__.py                 # CLI entry point with argparse
│   ├── config.py                   # Configuration management
│   ├── core/
│   │   ├── github_client.py        # GitHub API client
│   │   ├── logger.py               # Logging utilities
│   │   ├── types.py                # Core types (RepoContext, ActionResult, Status, OperationResult)
│   │   └── registry.py             # Unified generic registry
│   ├── predicates/                 # Composable predicates
│   │   ├── base.py                 # Predicate base class and combinators
│   │   └── core.py                 # Core predicates (RepoExists, RepoClean, etc.)
│   ├── actions/                    # Single-responsibility actions
│   │   ├── base.py                 # Action base class
│   │   ├── git.py                  # Git actions (CloneAction, PullAction)
│   │   ├── json_ops.py             # JSON manipulation actions
│   │   ├── subprocess_ops.py       # Subprocess actions (legacy fallback)
│   │   ├── claude_sdk.py           # Claude SDK actions (preferred)
│   │   └── description_sync.py     # Description sync action
│   ├── pipelines/                  # Composable pipelines
│   │   ├── base.py                 # Pipeline class with fluent API
│   │   ├── executor.py             # PipelineExecutor
│   │   ├── registry.py             # Pipeline registry
│   │   ├── git_ops.py              # Git pipelines (sync, clone-only, pull-only)
│   │   ├── settings_ops.py         # Settings pipelines (sandbox-enable, settings-clean)
│   │   ├── status_ops.py           # Status pipeline
│   │   └── subprocess_ops.py       # Subprocess pipelines (description-sync, claude-exec)
│   └── utils/
│       ├── git.py                  # Git helpers
│       ├── progress.py             # Progress tracking
│       ├── filters.py              # Repository filtering
│       └── async_bridge.py         # Sync-to-async utilities for SDK
├── pyproject.toml                  # Package configuration
└── uv.lock                         # Dependency lock file
```

### Pipeline Architecture

gitfleet uses a composable pipeline architecture that separates concerns into:
- **Predicates** - When to run (composable conditions)
- **Actions** - What to do (single-responsibility execution units)
- **Pipelines** - How to compose predicates and actions

**Key Packages:**
- `gitfleet/predicates/` - Composable predicates (RepoExists, RepoClean, NotArchived, etc.)
- `gitfleet/actions/` - Single-responsibility actions (CloneAction, PullAction, JsonPatchAction, etc.)
- `gitfleet/pipelines/` - Pipeline definitions and executor
- `gitfleet/core/types.py` - Core types (RepoContext, ActionResult, Status, OperationResult)
- `gitfleet/core/registry.py` - Unified generic registry

**Creating New Pipelines:**
```python
from gitfleet.pipelines import Pipeline
from gitfleet.predicates import RepoExists, RepoClean, not_
from gitfleet.actions import CloneAction, PullAction

class MyPipeline(Pipeline):
    name = "my-pipeline"
    description = "My custom pipeline"
    safe_parallel = True

    def __init__(self):
        super().__init__()
        # Define conditions and actions
        self.when(RepoExists())
        self.then(PullAction())
```

**Predicate Combinators:**
```python
from gitfleet.predicates import all_of, any_of, not_, RepoExists, RepoClean

# All conditions must pass
all_of(RepoExists(), RepoClean())

# Any condition passes
any_of(RepoExists(), FileExists("README.md"))

# Negate a predicate
not_(RepoExists())

# Use operators
RepoExists() & RepoClean()  # AND
RepoExists() | FileExists("README.md")  # OR
~RepoExists()  # NOT
```

**Adding New Pipelines:**
1. Create a pipeline class in the appropriate `pipelines/*.py` file
2. Inherit from `Pipeline` base class
3. Set class attributes: `name`, `description`, `requires_token`, `safe_parallel`
4. Define predicates with `when()` and actions with `then()` in `__init__`
5. Register the pipeline in `pipelines/registry.py`
6. Optionally override `post_batch_hook()` for aggregation/summary output

### Core Components

**GitHubClient** (`core/github_client.py`):
- GitHub API interactions with pagination
- Authenticated mode: `/user/repos` endpoint (all repos including private)
- Unauthenticated mode: `/users/{username}/repos` + org repos
- Clone URL selection: SSH when authenticated, HTTPS otherwise

**PipelineExecutor** (`pipelines/executor.py`):
- Orchestrates pipeline execution
- Parallel execution with ThreadPoolExecutor
- Sequential execution for rate-limited operations
- Pre-filters repositories using pipeline predicates
- Calls `post_batch_hook()` for aggregation after all repos processed

**RepoFilter** (`utils/filters.py`):
- Filter by: repo names, orgs, patterns (glob), visibility, fork/archived status
- Supports multiple criteria with AND logic

### Configuration

- `Config` class merges .env and CLI arguments
- CLI arguments override environment variables
- Required: `GITHUB_USERNAME`
- Optional: `GITHUB_TOKEN` (enables auth mode and parallelization)
- Always operates on current working directory

### Logging

- Pipeline-specific log files: `logs/github_{pipeline}_YYYYMMDD_HHMMSS.log`
- Dual output to both file and console
- Progress tracking with live updates: `[████████░░] 80% (40/50) ✓35 ⊘3 ✗2`

## Pipelines Overview

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
   - Categorizes repos: In sync, Unpushed changes, Unpulled changes, Diverged, Uncommitted changes, Detached HEAD, No remote tracking, Not cloned
   - Fetches from remote to ensure accurate status
   - Provides grouped summary output via `post_batch_hook()`

5. **claude-exec** - Execute Claude prompts via SDK
   - Parallelization: No (Claude API rate limits)
   - Supports raw prompts and skill invocations (e.g., "/readme-generator")
   - Pre-execution briefing with confirmation prompt (can skip with `--yes`)
   - Force mode (`--force`) to ignore pipeline predicates
   - Uses `claude-agent-sdk` for native Python integration, cost tracking, and better error handling
   - Falls back to subprocess if SDK not available
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

8. **description-sync** - Sync GitHub repo description with README tagline
   - Parallelization: Yes (independent gh CLI calls)
   - Extracts tagline from README.md (bold text in centered div, or first paragraph after title)
   - Updates GitHub repo description via `gh repo edit`
   - Truncates descriptions > 350 chars
   - Skips archived repos, repos without README, or when description already matches
   - Requires: `gh` CLI installed and authenticated

## Important Implementation Details

- Repositories with unstaged changes are skipped during pull operations to prevent data loss
- GitHub API pagination handled with 100 items per page
- Repository deduplication by ID to handle overlaps between user/org repos
- Default branch detection before pulling (uses `git rev-parse --abbrev-ref HEAD`)
- Rate limit detection with graceful exit on HTTP 403
- Thread-safe parallel processing for all pipelines marked as safe_parallel
- Dry-run mode available for all pipelines
- Comprehensive filtering: by repo name, org, pattern, visibility, fork/archived status
- Forked repositories are excluded by default (use `--include-forks` to include them)
- Archived repositories are excluded by default (use `--include-archived` to include them)

## Key Dependencies

- `requests`: GitHub API interaction
- `python-dotenv`: Environment variable management
- `claude-agent-sdk`: Claude Code SDK for native Python integration (async-native)
- `PyGithub`: Currently installed but not used in code (consider removing or utilizing)

## Important Note

README.md must be kept up to date with any significant project changes.
