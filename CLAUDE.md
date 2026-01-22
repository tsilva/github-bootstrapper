# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Bootstrapper is a multi-operation repository management system that performs bulk operations on GitHub repositories. It supports eight operations: sync (clone + pull), clone-only, pull-only, status (synchronization status reporting), claude-exec (execute Claude prompts using templates or raw prompts), settings-clean (Claude Code settings cleanup), sandbox-enable (enable Claude Code sandbox mode), and description-sync (sync GitHub repo description with README tagline). Features include parallel processing, flexible filtering, and an extensible operation framework.

## Prompt Templates

The `claude-exec` operation supports built-in prompt templates with intelligent filtering logic:

**Built-in Templates:**
- **init** - Initialize CLAUDE.md files (skips archived, forks, existing CLAUDE.md)

**Template Features:**
- Intelligent filtering via `should_run()` logic (can be overridden with `--force`)
- Variable substitution support:
  - `{{repo_name}}` - Repository name
  - `{{repo_full_name}}` - Full repository name (owner/repo)
  - `{{default_branch}}` - Default branch name
  - `{{description}}` - Repository description
  - `{{language}}` - Primary language
- Pre-execution briefing with confirmation prompt
- Sequential execution to respect Claude API rate limits

**Raw Prompts:**
You can also execute ad-hoc prompts by providing any text that doesn't match a template name. Raw prompts run on all locally cloned repositories (unless filtered).

**Extensibility:**
Add new templates by creating a Python file in `gitfleet/prompt_templates/` that inherits from `PromptTemplate`. The registry auto-discovers new templates via introspection.

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

Run operations (examples use global installation; for local dev, prefix with `uv run`):
```bash
# Check repository status
gitfleet status --username your-username

# Sync all repositories
gitfleet sync --username your-username

# Clone only missing repositories
gitfleet clone-only --username your-username --dry-run

# Pull updates for existing repositories
gitfleet pull-only --username your-username

# List available prompt templates
gitfleet --list-templates

# Execute using built-in templates (forks excluded by default)
gitfleet claude-exec init --username your-username

# Execute using raw prompts
gitfleet claude-exec "Add a LICENSE file" --username your-username

# Force execution (ignore should_run logic)
gitfleet claude-exec readme --force --username your-username

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
│   │   ├── repo_manager.py         # Operation orchestrator
│   │   └── logger.py               # Logging utilities
│   ├── operations/
│   │   ├── base.py                 # Abstract Operation class
│   │   ├── registry.py             # Auto-discovery via introspection
│   │   ├── sync.py                 # Clone + pull operation
│   │   ├── clone_only.py           # Clone-only operation
│   │   ├── pull_only.py            # Pull-only operation
│   │   ├── status.py               # Repository status operation
│   │   ├── claude_exec.py          # Execute Claude prompts
│   │   ├── settings_clean.py       # Settings cleanup via script
│   │   ├── sandbox_enable.py       # Sandbox mode enablement
│   │   └── description_sync.py     # Sync repo description with README
│   ├── prompt_templates/
│   │   ├── base.py                 # Abstract PromptTemplate class
│   │   ├── registry.py             # Template auto-discovery
│   │   ├── init.py                 # CLAUDE.md initialization template
│   │   └── raw.py                  # Raw prompt template
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
- Required: `GITHUB_USERNAME`
- Optional: `GITHUB_TOKEN` (enables auth mode and parallelization)
- Always operates on current working directory

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

5. **claude-exec** - Execute Claude prompts using templates or raw prompts
   - Parallelization: No (Claude API rate limits)
   - Supports built-in templates with intelligent filtering
   - Variable substitution in prompts: `{{repo_name}}`, `{{repo_full_name}}`, etc.
   - Pre-execution briefing with confirmation prompt (can skip with `--yes`)
   - Templates: init (CLAUDE.md)
   - Can use raw prompts for ad-hoc tasks
   - Force mode (`--force`) to ignore template `should_run()` logic
   - Invokes Claude CLI: `claude -p "prompt" --permission-mode acceptEdits --output-format json`
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
- Thread-safe parallel processing for all operations marked as safe_parallel (no token required)
- Dry-run mode available for all operations
- Comprehensive filtering: by repo name, org, pattern, visibility, fork/archived status
- Forked repositories are excluded by default (use `--include-forks` to include them)
- Archived repositories are excluded by default (use `--include-archived` to include them)

## Key Dependencies

- `requests`: GitHub API interaction
- `python-dotenv`: Environment variable management
- `PyGithub`: Currently installed but not used in code (consider removing or utilizing)

## Important Note

README.md must be kept up to date with any significant project changes.
