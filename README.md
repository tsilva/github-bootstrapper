<div align="center">
  <img src="logo.png" alt="github-bootstrapper" width="280"/>

  [![Build](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/tsilva/github-bootstrapper)
  [![Python](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![uv](https://img.shields.io/badge/uv-enabled-blueviolet)](https://github.com/astral-sh/uv)

  **Bulk repository operations powered by parallel processing - sync, clone, pull, and automate Claude Code workflows across all your GitHub repos**

  [Quick Start](#quick-start) · [Operations](#operations) · [Examples](#examples)
</div>

---

## Overview

github-bootstrapper is a multi-operation CLI that manages your entire GitHub repository portfolio. Clone missing repos, pull updates, generate READMEs with Claude, enable sandbox mode, and clean settings - all with parallel processing and intelligent filtering.

Perfect for developers managing dozens (or hundreds) of repositories who want to:
- Keep local checkouts in sync without manual git commands
- Apply consistent configurations across all projects
- Automate documentation and settings management
- Filter operations by org, visibility, patterns, or specific repos

## Features

- **7 Powerful Operations** - sync, clone-only, pull-only, status, readme-gen, sandbox-enable, settings-clean
- **Parallel Processing** - utilize all CPU cores for thread-safe operations (when authenticated)
- **Flexible Filtering** - target repos by name, org, pattern, visibility, or exclude forks/archived
- **Dry-Run Mode** - preview changes before executing
- **Claude Integration** - generate READMEs and clean settings using Claude Code skills
- **Smart Safety** - automatically skips repos with unstaged changes during pull operations
- **Authenticated & Unauthenticated Modes** - SSH URLs with token, HTTPS without
- **Live Progress** - visual progress bar with success/skip/fail counts
- **Operation Framework** - extensible architecture makes adding new operations trivial

## Quick Start

### Installation

**Option 1: Global Installation (Recommended)**

Install once, run from anywhere:

```bash
# Clone and install globally
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper
uv tool install .

# Now run from any directory containing your repos
cd ~/repos/your-username
github-bootstrapper status --username your-username
```

**Option 2: Local Installation**

```bash
# Clone the repository
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper

# Install dependencies
uv sync

# Run with uv
uv run github-bootstrapper sync
```

### Configuration

**Global Installation:** Run from your repos directory with `--username`:

```bash
cd ~/repos/your-username
github-bootstrapper sync --username your-username
```

**Local Installation:** Create a `.env` file (use `.env.example` as template):

```env
GITHUB_USERNAME=your_github_username
REPOS_BASE_DIR=/path/to/your/repos/directory  # Defaults to current directory
GITHUB_TOKEN=your_github_token  # Optional but recommended
```

**Why provide a token?**
- Access private and organization repositories
- Enable parallel processing (faster operations)
- Use SSH URLs for cloning (no password prompts)

### First Run

**Global Installation:**
```bash
cd ~/repos/your-username
github-bootstrapper sync --username your-username --dry-run
github-bootstrapper sync --username your-username
```

**Local Installation:**
```bash
uv run github-bootstrapper sync --dry-run
uv run github-bootstrapper sync
```

## Operations

### 1. sync

Clone new repositories and pull updates for existing ones.

```bash
# Sync all repos
uv run github-bootstrapper sync

# Dry-run to preview
uv run github-bootstrapper sync --dry-run

# Sync only private repos from a specific org
uv run github-bootstrapper sync --org mycompany --private-only
```

**Behavior:**
- Clones repos that don't exist locally
- Pulls updates for repos that exist
- Skips repos with unstaged changes
- Thread-safe parallel execution

---

### 2. clone-only

Clone repositories that don't exist locally (skip existing).

```bash
# Clone all missing repos
uv run github-bootstrapper clone-only

# Clone only repos matching pattern
uv run github-bootstrapper clone-only --pattern "my-*"
```

**Behavior:**
- Only clones missing repositories
- Skips repos that already exist
- Thread-safe parallel execution

---

### 3. pull-only

Pull updates for repositories that exist locally (skip missing).

```bash
# Pull updates for all existing repos
uv run github-bootstrapper pull-only

# Use 8 parallel workers
uv run github-bootstrapper pull-only --workers 8
```

**Behavior:**
- Only pulls existing repositories
- Skips repos that don't exist locally
- Skips repos with unstaged changes
- Thread-safe parallel execution

---

### 4. status

Report synchronization status of all repositories.

```bash
# Check status of all repos
github-bootstrapper status --username your-username

# Check specific repos
github-bootstrapper status --username your-username --repo repo1 --repo repo2

# Check only private repos
github-bootstrapper status --username your-username --private-only
```

**Behavior:**
- Categorizes repos: In sync, Unpushed changes, Unpulled changes, Diverged, Uncommitted changes, Not cloned
- Fetches from remote for accurate status
- Provides grouped summary output
- Thread-safe parallel execution

---

### 5. readme-gen

Generate or update README.md using Claude's readme-generator skill.

```bash
# Generate READMEs for repos without one
uv run github-bootstrapper readme-gen

# Force regenerate even if README exists
uv run github-bootstrapper readme-gen --force

# Generate only for non-fork repos
uv run github-bootstrapper readme-gen --exclude-forks
```

**Behavior:**
- Invokes Claude CLI: `claude -p "prompt" --permission-mode acceptEdits`
- Skips archived and fork repos by default
- Sequential execution (Claude API rate limits)
- 5-minute timeout per repository

**Requirements:**
- Claude Code CLI installed and authenticated
- readme-generator skill available

---

### 6. sandbox-enable

Enable Claude Code sandbox mode with auto-allow bash for all repos.

```bash
# Enable sandbox for all repos
uv run github-bootstrapper sandbox-enable

# Enable for specific repos
uv run github-bootstrapper sandbox-enable --repo repo1 --repo repo2
```

**Behavior:**
- Creates or updates `.claude/settings.local.json`
- Sets: `{"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true}}`
- Preserves existing settings
- Thread-safe parallel execution

---

### 7. settings-clean

Analyze and clean Claude Code permission whitelists.

```bash
# Analyze settings (default mode)
uv run github-bootstrapper settings-clean

# Clean settings interactively
uv run github-bootstrapper settings-clean --mode clean

# Auto-fix issues
uv run github-bootstrapper settings-clean --mode auto-fix
```

**Behavior:**
- Invokes settings-cleaner script via `uv run`
- Modes: analyze, clean, auto-fix
- Skips repos without `.claude/settings.local.json`
- Thread-safe parallel execution

**Requirements:**
- settings-cleaner skill installed

## Filtering

All operations support powerful filtering options:

| Filter | Description | Example |
|--------|-------------|---------|
| `--repo NAME` | Target specific repo(s) | `--repo my-app --repo another-app` |
| `--org NAME` | Filter by organization | `--org mycompany --org otherorg` |
| `--pattern GLOB` | Filter by name pattern | `--pattern "web-*"` |
| `--exclude-forks` | Exclude forked repos | `--exclude-forks` |
| `--exclude-archived` | Exclude archived repos | `--exclude-archived` |
| `--private-only` | Only private repos | `--private-only` |
| `--public-only` | Only public repos | `--public-only` |

### Filter Examples

```bash
# Sync only private repos from your company
uv run github-bootstrapper sync --org mycompany --private-only

# Generate READMEs for your personal projects (exclude forks)
uv run github-bootstrapper readme-gen --pattern "my-*" --exclude-forks

# Enable sandbox only for active development repos
uv run github-bootstrapper sandbox-enable --exclude-archived

# Pull updates for specific repos
uv run github-bootstrapper pull-only --repo web-app --repo api-server
```

## Examples

> **Note:** Examples show global installation commands. For local installation, prefix with `uv run`.

### Daily Workflow

```bash
# Navigate to your repos directory
cd ~/repos/your-username

# Morning: update all repos
github-bootstrapper pull-only --username your-username

# Check what's new (dry-run)
github-bootstrapper clone-only --username your-username --dry-run

# Clone any new repos
github-bootstrapper clone-only --username your-username
```

### Check Repository Status

```bash
# See sync status of all repos
github-bootstrapper status --username your-username

# Check specific repos
github-bootstrapper status --username your-username --repo project1 --repo project2

# Check only private repos
github-bootstrapper status --username your-username --private-only
```

### Bulk Configuration

```bash
# Enable sandbox mode everywhere
github-bootstrapper sandbox-enable --username your-username

# Analyze all Claude settings
github-bootstrapper settings-clean --username your-username --mode analyze

# Auto-fix issues in settings
github-bootstrapper settings-clean --username your-username --mode auto-fix
```

### Documentation Sprint

```bash
# Generate READMEs for all personal projects (excluding forks)
github-bootstrapper readme-gen --username your-username --exclude-forks --exclude-archived

# Force regenerate for specific repos
github-bootstrapper readme-gen --username your-username --force --repo my-main-project
```

### Fresh Machine Setup

```bash
# Navigate to where you want your repos
cd ~/repos/your-username

# Clone all your repos
github-bootstrapper clone-only --username your-username

# Enable sandbox mode for all
github-bootstrapper sandbox-enable --username your-username

# Generate missing READMEs
github-bootstrapper readme-gen --username your-username
```

## Global Options

All operations support these flags:

| Flag | Description |
|------|-------------|
| `--repos-dir PATH` | Override REPOS_BASE_DIR |
| `--username USER` | Override GITHUB_USERNAME |
| `--token TOKEN` | Override GITHUB_TOKEN |
| `--workers N` | Number of parallel workers (default: CPU count) |
| `--sequential` | Force sequential processing |
| `--dry-run` | Preview without executing |

## Architecture

github-bootstrapper uses an extensible **Operation Framework** based on the Strategy Pattern:

```
github_bootstrapper/
├── core/
│   ├── github_client.py    # GitHub API with pagination
│   ├── repo_manager.py     # Orchestrates operations
│   └── logger.py           # Operation-specific logging
├── operations/
│   ├── base.py             # Abstract Operation class
│   ├── registry.py         # Auto-discovery via introspection
│   ├── sync.py             # Clone + pull
│   ├── clone_only.py       # Clone missing
│   ├── pull_only.py        # Pull existing
│   ├── readme_gen.py       # README generation
│   ├── settings_clean.py   # Settings cleanup
│   └── sandbox_enable.py   # Sandbox enablement
└── utils/
    ├── git.py              # Git helpers
    ├── filters.py          # Repository filtering
    └── progress.py         # Progress tracking
```

### Adding New Operations

Create a new operation in 3 steps:

1. **Create file** in `operations/` directory
2. **Inherit from Operation** base class
3. **Implement `execute()` method**

```python
from .base import Operation, OperationResult, OperationStatus

class MyOperation(Operation):
    name = "my-op"
    description = "Does something useful"
    requires_token = False
    safe_parallel = True

    def execute(self, repo, repo_path):
        # Your logic here
        return OperationResult(
            status=OperationStatus.SUCCESS,
            message="Done!",
            repo_name=repo['name'],
            repo_full_name=repo['full_name']
        )
```

The registry auto-discovers it - no other changes needed!

## Authentication Modes

### Authenticated Mode (Recommended)

With a GitHub token:
- ✅ Access private and organization repos
- ✅ Parallel processing (faster)
- ✅ SSH URLs (no password prompts)
- ✅ Higher API rate limits

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### Unauthenticated Mode

Without a token:
- ⚠️ Public repos only
- ⚠️ Sequential processing
- ⚠️ HTTPS URLs (may prompt for credentials)
- ⚠️ Lower API rate limits

## Progress Tracking

Operations display live progress with success/skip/fail counts:

```
[████████████████░░░░] 80% (40/50) ✓35 ⊘3 ✗2
```

**Legend:**
- ✓ Success
- ⊘ Skipped
- ✗ Failed

Final summary includes detailed failure messages:

```
============================================================
SUMMARY: SYNC
============================================================
Total repositories: 50
✓ Success: 35
⊘ Skipped: 3
✗ Failed: 2

Failed repositories:
  - user/broken-repo: Failed to pull changes
  - user/archived-repo: Repository has unstaged changes
============================================================
```

## Requirements

- Python 3.8+
- uv (package manager)
- git
- GitHub account
- Claude Code CLI (for readme-gen operation)

## Contributing

Contributions are welcome! This project follows an extensible architecture that makes adding new operations straightforward.

### Development Setup

```bash
# Clone and install
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper
uv sync

# Run tests (if available)
uv run pytest

# Try your changes
uv run github-bootstrapper --help
```

### Contribution Ideas

- New operations (PR creation, dependency updates, license compliance)
- Additional filters (by language, by activity, by size)
- Enhanced progress tracking
- Operation result export (JSON, CSV)
- Configuration profiles

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Tiago Silva

---

<div align="center">
  Made with ❤️ by developers who manage too many repos

  If this helps you, please ⭐ star the repo!
</div>
