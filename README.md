<div align="center">
  <img src="logo.png" alt="gitfleet" width="512"/>

  [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![GitHub](https://img.shields.io/badge/GitHub-tsilva%2Fgitfleet-blue?logo=github)](https://github.com/tsilva/gitfleet)

  **🚢 Bulk operations across all your GitHub repositories with parallel processing and smart filtering ⚡**

</div>

## Overview

[![CI](https://github.com/tsilva/gitfleet/actions/workflows/release.yml/badge.svg)](https://github.com/tsilva/gitfleet/actions/workflows/release.yml)

gitfleet is a CLI tool that performs bulk operations on your GitHub repositories. Sync, clone, pull, check status, or execute Claude prompts across dozens of repos in one command.

## Features

- ⚡ **Parallel Processing** - Thread-safe operations for maximum speed
- 🔍 **Smart Filtering** - Filter by name, org, pattern, visibility, fork/archived status
- 🤖 **Claude Integration** - Execute AI prompts across repos with template support
- 📊 **Status Reporting** - See sync state of all repos at a glance
- 🛡️ **Safe Operations** - Skips repos with uncommitted changes, dry-run mode available
- 🔌 **Extensible** - Add custom operations via simple plugin architecture

## Quick Start

```bash
# Install globally
uv tool install gitfleet

# Or for development
uv sync
```

Create a `.env` file:
```bash
GITHUB_USERNAME=your_username
GITHUB_TOKEN=your_token  # Optional but recommended
```

Run from the directory containing your repositories:
```bash
# Check status of all repos
gitfleet status --username your-username

# Sync everything (clone new + pull existing)
gitfleet sync --username your-username
```

## Operations

| Operation | Description | Parallel |
|-----------|-------------|----------|
| `sync` | Clone new repos + pull existing | ✅ |
| `clone-only` | Only clone repos not yet cloned | ✅ |
| `pull-only` | Only pull updates for existing repos | ✅ |
| `status` | Report repository sync status | ✅ |
| `claude-exec` | Execute Claude prompts using templates | ❌ |
| `settings-clean` | Analyze/clean Claude Code settings | ✅ |
| `sandbox-enable` | Enable Claude Code sandbox mode | ✅ |
| `description-sync` | Sync GitHub description with README tagline | ✅ |

## Usage Examples

```bash
# Clone only, dry-run first
gitfleet clone-only --username your-username --dry-run

# Pull updates for existing repos
gitfleet pull-only --username your-username

# Execute Claude prompt template
gitfleet claude-exec init --username your-username

# Execute raw prompt across repos
gitfleet claude-exec "Add a LICENSE file" --username your-username

# Filter by pattern
gitfleet sync --username your-username --pattern "my-project-*"

# Include forks and archived repos
gitfleet status --username your-username --include-forks --include-archived
```

## Filtering

```bash
# By repository name
--repos repo1,repo2,repo3

# By organization
--orgs org1,org2

# By glob pattern
--pattern "prefix-*"

# By visibility
--visibility public|private

# Include usually-excluded repos
--include-forks
--include-archived
```

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `GITHUB_USERNAME` | Yes | Your GitHub username |
| `GITHUB_TOKEN` | No | Personal access token (enables private repos + parallel processing) |

## Adding Custom Operations

1. Create a file in `gitfleet/operations/`
2. Inherit from `Operation` base class
3. Implement `execute()` method
4. Set class attributes: `name`, `description`, `requires_token`, `safe_parallel`

The registry auto-discovers new operations - no additional configuration needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
