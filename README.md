<div align="center">
  <img src="logo.png" alt="gitfleet" width="512"/>

  [![Build](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/tsilva/gitfleet)
  [![Python](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![uv](https://img.shields.io/badge/uv-enabled-blueviolet)](https://github.com/astral-sh/uv)

  **Bulk repository operations powered by parallel processing - sync, clone, pull, and automate Claude Code workflows across all your GitHub repos**

  [Quick Start](#quick-start) · [Operations](#operations) · [Examples](#examples)
</div>

---

## Overview

gitfleet is a multi-operation CLI that manages your entire GitHub repository portfolio. Clone missing repos, pull updates, execute Claude prompts with templates, enable sandbox mode, and clean settings - all with parallel processing and intelligent filtering.

Perfect for developers managing dozens (or hundreds) of repositories who want to:
- Keep local checkouts in sync without manual git commands
- Apply consistent configurations across all projects
- Automate documentation and settings management with Claude Code
- Filter operations by org, visibility, patterns, or specific repos

## Features

- **8 Powerful Operations** - sync, clone-only, pull-only, status, claude-exec, sandbox-enable, settings-clean, description-sync
- **Parallel Processing** - utilize all CPU cores for thread-safe operations
- **Flexible Filtering** - target repos by name, org, pattern, visibility, or exclude forks/archived
- **Dry-Run Mode** - preview changes before executing
- **Claude Integration** - execute prompts using built-in templates or raw prompts
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
git clone https://github.com/tsilva/gitfleet.git
cd gitfleet
uv tool install .

# Now run from any directory containing your repos
cd ~/repos/your-username
gitfleet status --username your-username
```

**Option 2: Local Installation**

```bash
# Clone the repository
git clone https://github.com/tsilva/gitfleet.git
cd gitfleet

# Install dependencies
uv sync

# Run with uv
uv run gitfleet sync
```

### Configuration

**Global Installation:** Run from your repos directory with `--username`:

```bash
cd ~/repos/your-username
gitfleet sync --username your-username
```

**Local Installation:** Create a `.env` file (use `.env.example` as template):

```env
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_token  # Optional but recommended
```

> **Note:** Always run from the directory containing your repositories.

**Why provide a token?**
- Access private and organization repositories
- Enable parallel processing (faster operations)
- Use SSH URLs for cloning (no password prompts)

### First Run

**Global Installation:**
```bash
cd ~/repos/your-username
gitfleet sync --username your-username --dry-run
gitfleet sync --username your-username
```

**Local Installation:**
```bash
uv run gitfleet sync --dry-run
uv run gitfleet sync
```

## Operations

### 1. sync

Clone new repositories and pull updates for existing ones.

```bash
# Sync all repos
gitfleet sync --username your-username

# Dry-run to preview
gitfleet sync --username your-username --dry-run

# Sync only private repos from a specific org
gitfleet sync --username your-username --org mycompany --private-only
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
gitfleet clone-only --username your-username

# Clone only repos matching pattern
gitfleet clone-only --username your-username --pattern "my-*"
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
gitfleet pull-only --username your-username

# Use 8 parallel workers
gitfleet pull-only --username your-username --workers 8
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
gitfleet status --username your-username

# Check specific repos
gitfleet status --username your-username --repo repo1 --repo repo2

# Check only private repos
gitfleet status --username your-username --private-only
```

**Behavior:**
- Categorizes repos: In sync, Unpushed changes, Unpulled changes, Diverged, Uncommitted changes, Not cloned
- Fetches from remote for accurate status
- Provides grouped summary output
- Thread-safe parallel execution (8 workers by default)

---

### 5. claude-exec

Execute Claude prompts using built-in templates or raw prompts.

```bash
# List available templates
gitfleet --list-templates

# Execute using built-in templates
gitfleet claude-exec init --username your-username

# Execute raw prompts
gitfleet claude-exec "Add a LICENSE file" --username your-username

# Force execution (ignore template should_run logic)
gitfleet claude-exec init --username your-username --force

# Skip confirmation prompt
gitfleet claude-exec init --username your-username --yes
```

**Built-in Templates:**
| Template | Description |
|----------|-------------|
| `init` | Initialize CLAUDE.md files (skips archived, forks, existing CLAUDE.md) |

**Behavior:**
- Invokes Claude CLI: `claude -p "prompt" --permission-mode acceptEdits --output-format json`
- Pre-execution briefing with confirmation prompt (can skip with `--yes`)
- Supports variable substitution: `{{repo_name}}`, `{{repo_full_name}}`, `{{default_branch}}`, `{{description}}`, `{{language}}`
- Sequential execution (Claude API rate limits)
- 5-minute timeout per repository

**Requirements:**
- Claude Code CLI installed and authenticated

---

### 6. sandbox-enable

Enable Claude Code sandbox mode with auto-allow bash for all repos.

```bash
# Enable sandbox for all repos
gitfleet sandbox-enable --username your-username

# Enable for specific repos
gitfleet sandbox-enable --username your-username --repo repo1 --repo repo2
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
gitfleet settings-clean --username your-username

# Clean settings interactively
gitfleet settings-clean --username your-username --mode clean

# Auto-fix issues
gitfleet settings-clean --username your-username --mode auto-fix
```

**Behavior:**
- Invokes settings-cleaner script via `uv run`
- Modes: analyze, clean, auto-fix
- Skips repos without `.claude/settings.local.json`
- Thread-safe parallel execution

**Requirements:**
- settings-cleaner skill installed

---

### 8. description-sync

Sync GitHub repository descriptions with README taglines.

```bash
# Preview changes (dry-run)
gitfleet description-sync --username your-username --dry-run

# Sync descriptions for all repos
gitfleet description-sync --username your-username

# Sync for specific repos
gitfleet description-sync --username your-username --repo repo1 --repo repo2
```

**Tagline Extraction (priority order):**
1. Bold text (`**...**`) within `<div align="center">` block
2. First paragraph after `# Title`

**Behavior:**
- Updates GitHub repo description via `gh repo edit`
- Truncates descriptions exceeding 350 characters
- Skips archived repos (can't update)
- Skips repos without README.md
- Skips when description already matches tagline
- Thread-safe parallel execution

**Requirements:**
- `gh` CLI installed and authenticated (`gh auth login`)

## Filtering

All operations support powerful filtering options:

| Filter | Description | Example |
|--------|-------------|---------|
| `--repo NAME` | Target specific repo(s) | `--repo my-app --repo another-app` |
| `--org NAME` | Filter by organization | `--org mycompany --org otherorg` |
| `--pattern GLOB` | Filter by name pattern | `--pattern "web-*"` |
| `--include-forks` | Include forked repos (excluded by default) | `--include-forks` |
| `--include-archived` | Include archived repos (excluded by default) | `--include-archived` |
| `--private-only` | Only private repos | `--private-only` |
| `--public-only` | Only public repos | `--public-only` |

### Filter Examples

```bash
# Sync only private repos from your company
gitfleet sync --username your-username --org mycompany --private-only

# Execute prompts for your personal projects (exclude forks)
gitfleet claude-exec "Update copyright year" --username your-username --pattern "my-*"

# Enable sandbox only for active development repos
gitfleet sandbox-enable --username your-username

# Pull updates for specific repos
gitfleet pull-only --username your-username --repo web-app --repo api-server
```

## Examples

### Daily Workflow

```bash
# Navigate to your repos directory
cd ~/repos/your-username

# Morning: update all repos
gitfleet pull-only --username your-username

# Check what's new (dry-run)
gitfleet clone-only --username your-username --dry-run

# Clone any new repos
gitfleet clone-only --username your-username
```

### Check Repository Status

```bash
# See sync status of all repos
gitfleet status --username your-username

# Check specific repos
gitfleet status --username your-username --repo project1 --repo project2

# Check only private repos
gitfleet status --username your-username --private-only
```

### Bulk Configuration

```bash
# Enable sandbox mode everywhere
gitfleet sandbox-enable --username your-username

# Analyze all Claude settings
gitfleet settings-clean --username your-username --mode analyze

# Auto-fix issues in settings
gitfleet settings-clean --username your-username --mode auto-fix
```

### Documentation Sprint

```bash
# Initialize CLAUDE.md for all projects
gitfleet claude-exec init --username your-username

# Execute raw prompt for documentation
gitfleet claude-exec "/readme-generator" --username your-username
```

### Fresh Machine Setup

```bash
# Navigate to where you want your repos
cd ~/repos/your-username

# Clone all your repos
gitfleet clone-only --username your-username

# Enable sandbox mode for all
gitfleet sandbox-enable --username your-username

# Initialize CLAUDE.md files
gitfleet claude-exec init --username your-username
```

## Global Options

All operations support these flags:

| Flag | Description |
|------|-------------|
| `--username USER` | Override GITHUB_USERNAME |
| `--token TOKEN` | Override GITHUB_TOKEN |
| `--workers N` | Number of parallel workers (default: CPU count) |
| `--sequential` | Force sequential processing |
| `--dry-run` | Preview without executing |

## Architecture

gitfleet uses an extensible **Operation Framework** based on the Strategy Pattern:

```
gitfleet/
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
│   ├── status.py           # Status reporting
│   ├── claude_exec.py      # Execute Claude prompts
│   ├── settings_clean.py   # Settings cleanup
│   ├── sandbox_enable.py   # Sandbox enablement
│   └── description_sync.py # Description sync
├── prompt_templates/
│   ├── base.py             # Abstract PromptTemplate class
│   ├── registry.py         # Template auto-discovery
│   ├── init.py             # CLAUDE.md initialization
│   └── raw.py              # Raw prompt wrapper
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

### Adding New Prompt Templates

Create a new template in `prompt_templates/` directory:

```python
from .base import PromptTemplate

class MyTemplate(PromptTemplate):
    name = "my-template"
    description = "Does something with Claude"
    prompt = "Your prompt here with {{repo_name}} variables"

    def should_run(self, repo, repo_path):
        # Return (True, None) to run, or (False, "reason") to skip
        return True, None
```

## Authentication Modes

### Authenticated Mode (Recommended)

With a GitHub token:
- Access private and organization repos
- Parallel processing (faster)
- SSH URLs (no password prompts)
- Higher API rate limits

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### Unauthenticated Mode

Without a token:
- Public repos only
- Sequential processing
- HTTPS URLs (may prompt for credentials)
- Lower API rate limits

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
- Claude Code CLI (for claude-exec operation)

## Contributing

Contributions are welcome! This project follows an extensible architecture that makes adding new operations straightforward.

### Development Setup

```bash
# Clone and install
git clone https://github.com/tsilva/gitfleet.git
cd gitfleet
uv sync

# Run tests (if available)
uv run pytest

# Try your changes
uv run gitfleet --help
```

### Contribution Ideas

- New operations (PR creation, dependency updates, license compliance)
- New prompt templates (documentation, testing, linting)
- Additional filters (by language, by activity, by size)
- Enhanced progress tracking
- Operation result export (JSON, CSV)
- Configuration profiles

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Tiago Silva

---

<div align="center">
  Made with care by developers who manage too many repos

  If this helps you, please star the repo!
</div>
