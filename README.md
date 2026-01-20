<div align="center">
  <img src="logo.png" alt="github-bootstrapper" width="280"/>

  [![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

  **Sync all your GitHub repositories locally with parallel processing and smart change detection**

</div>

## Overview

GitHub Bootstrapper efficiently syncs all your GitHub repositories to your local machine. It automatically discovers repositories (including those in organizations), clones missing ones, and updates existing ones. With GitHub token support, it accesses private repositories and uses parallel processing for blazing-fast syncing.

## Features

- **Complete Repository Discovery** - Automatically finds all accessible repositories (public, private, and organization repos)
- **Parallel Processing** - When authenticated with a GitHub token, syncs multiple repositories concurrently using all CPU cores
- **Smart Change Detection** - Skips repositories with unstaged changes to prevent data loss
- **Detailed Logging** - Timestamped logs in the `logs/` directory for every sync session
- **Token-Aware Cloning** - Uses SSH URLs when token is available, HTTPS otherwise

## Quick Start

Install with `uv`:

```bash
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper
uv sync
```

Create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your settings
```

Run the sync:

```bash
uv run python main.py
```

## Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Clone the repository
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper

# Install dependencies with uv
uv sync
```

### Traditional Method

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root (copy from `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_USERNAME` | Yes | Your GitHub username |
| `REPOS_BASE_DIR` | Yes | Directory where repositories will be cloned/synced |
| `GITHUB_TOKEN` | No | GitHub personal access token (enables private repos + parallel processing) |

**Example `.env`:**

```bash
GITHUB_USERNAME=tsilva
REPOS_BASE_DIR=/Users/tsilva/repos
GITHUB_TOKEN=ghp_your_token_here  # Optional but recommended
```

### GitHub Token Setup

A GitHub token is optional but highly recommended. It provides:
- Access to private repositories
- Parallel processing (much faster syncing)
- Higher API rate limits
- SSH clone URLs (more secure)

[Create a GitHub token](https://github.com/settings/tokens) with `repo` scope.

## Usage

### Basic Usage

```bash
# Using uv
uv run python main.py

# Or activate virtual environment first
source .venv/bin/activate  # uv creates .venv by default
python main.py
```

### What Happens During Sync

1. **Discovery** - Fetches all accessible repositories via GitHub API
2. **Clone** - Clones any repositories not present locally
3. **Update** - Pulls latest changes for existing repositories
4. **Safety** - Skips repositories with unstaged changes
5. **Logging** - Creates detailed logs in `logs/github_sync_YYYYMMDD_HHMMSS.log`

### Processing Modes

| Mode | Trigger | Speed | Clone Method |
|------|---------|-------|--------------|
| **Parallel** | `GITHUB_TOKEN` set | Fast (uses all CPU cores) | SSH URLs |
| **Sequential** | No token | Slower (one-by-one) | HTTPS URLs |

## How It Works

### Architecture

- **Authenticated Mode** (with token): Uses `/user/repos` endpoint to fetch all repositories (public + private + org repos) in a single paginated request, then processes them in parallel using `ThreadPoolExecutor`

- **Unauthenticated Mode** (without token): Uses `/users/{username}/repos` for public repositories, fetches organization memberships separately, then processes sequentially

### Safety Features

- **Unstaged Change Detection**: Repositories with uncommitted changes are automatically skipped to prevent data loss
- **Deduplication**: Repositories are deduplicated by ID to handle overlaps between user and organization repos
- **Branch Awareness**: Detects the current branch before pulling (doesn't assume `main` or `master`)

## Logs

Every sync session creates a timestamped log file:

```
logs/
├── github_sync_20260120_143022.log
├── github_sync_20260120_150145.log
└── github_sync_20260120_153301.log
```

Logs include:
- Repository discovery details
- Clone/pull operations
- Skipped repositories (with reasons)
- Error messages with full context

## Requirements

- Python 3.8 or higher
- Git installed and accessible in PATH
- Internet connection
- (Optional) GitHub personal access token

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Made with ❤️ by Tiago Silva
</div>
