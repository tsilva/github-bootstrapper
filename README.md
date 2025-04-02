# 🔄 github-bootstrapper

<p align="center">
  <img src="logo.jpg" alt="Logo" width="400"/>
</p>


🚀 Sync all your GitHub repositories locally with parallel processing and smart change detection

## 📖 Overview

GitHub Bootstrapper is a tool that efficiently syncs all your GitHub repositories to your local machine. It automatically discovers your repositories (including those in organizations), clones missing ones, and updates existing ones. With GitHub token support, it can access private repositories and utilize parallel processing for faster syncing.

## 🚀 Installation

```bash
git clone https://github.com/username/github-bootstrapper.git
cd github-bootstrapper
chmod +x install.sh && ./install.sh
```

## ⚙️ Configuration

Create a `.env` file in the project root (or copy from `.env.example`):

```
GITHUB_USERNAME=your_github_username
REPOS_BASE_DIR=/path/to/your/repos/directory
# Optional: Add your GitHub token for private repos and parallel processing
GITHUB_TOKEN=your_github_token
```

Make sure the `REPOS_BASE_DIR` directory exists before running the script.

## 🛠️ Usage

Run the script with:

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
python main.py
```

The script will:
1. Fetch all accessible repositories (public + private with token)
2. Clone missing repositories
3. Update existing repositories
4. Skip repositories with unstaged changes
5. Create detailed logs in the `logs` directory

## ✨ Features

- Supports both public and private repositories
- Parallel processing with GitHub token for faster syncing
- Detects and skips repositories with unstaged changes
- Includes organization repositories
- Detailed logging with timestamps
- Automatically handles repository updates

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.