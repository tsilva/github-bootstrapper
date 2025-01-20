# 🔄 GitHub Bootstrapper

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🔄 Efficiently sync all your GitHub repositories locally with parallel processing support

## ✨ Features

- 🔑 Optional GitHub token support for private repositories
- ⚡ Parallel processing with multiple threads when using token
- 🔄 Automatic repository syncing and updates
- 📁 Organized local repository management
- 📝 Detailed logging with session tracking
- 🏢 Support for organization repositories
- ⚠️ Unstaged changes detection

## 🛠️ Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/yourusername/github-bootstrapper.git
   ```
2. Navigate to the project directory:
   ```sh
   cd github-bootstrapper
   ```
3. Install required packages:
   ```sh
   pip install -r requirements.txt
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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
