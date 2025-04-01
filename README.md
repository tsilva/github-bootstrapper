# 🔄 GitHub Bootstrapper

> 🔄 Efficiently sync all your GitHub repositories locally with parallel processing support

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <img src="logo.jpg" alt="PDF Merger Logo" width="400"/>
</p>

## ✨ Features

- 🔑 Optional GitHub token support for private repositories
- ⚡ Parallel processing with multiple threads when using token
- 🔄 Automatic repository syncing and updates
- 📁 Organized local repository management
- 📝 Detailed logging with session tracking
- 🏢 Support for organization repositories
- ⚠️ Unstaged changes detection

## ⚙️ Setup

```bash
git clone https://github.com/tsilva/github-bootstrapper.git
cd github-bootstrapper
curl -L https://gist.githubusercontent.com/tsilva/258374c1ba2296d8ba22fffbf640f183/raw/venv-install.sh -o install.sh && chmod +x install.sh && ./install.sh
```

```bash
curl -L https://gist.githubusercontent.com/tsilva/8588cb367242e3db8f1b33c42e4e5e06/raw/venv-run.sh -o run.sh && chmod +x run.sh && ./run.sh
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```properties
GITHUB_USERNAME=your_github_username
REPOS_BASE_DIR=/path/to/your/repos/directory
# Optional: Add your GitHub token for private repos and parallel processing
GITHUB_TOKEN=your_github_token
```

⚠️ Make sure the REPOS_BASE_DIR directory exists before running the script!

## 🚀 Usage

Simply run:
```sh
python main.py
```

The script will:
1. Fetch all accessible repositories (public + private with token)
2. Clone missing repositories
3. Update existing repositories
4. Skip repositories with unstaged changes
5. Create detailed logs in the `logs` directory

## 📝 Logging

Each run creates a unique log file:
```
logs/github_sync_YYYYMMDD_HHMMSS.log
```

Logs include:
- Repository discovery details
- Clone/update operations
- Success/failure status
- Processing mode (parallel/sequential)
