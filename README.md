# github-bootstrapper

A tool to automatically sync all your GitHub repositories using PyGithub.

## Setup

1. Clone this repository

2. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the .env file:
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub username and token
   ```

5. Run the script:
   ```bash
   python main.py
   ```

## Configuration

The `.env` file supports the following variables:
- `GITHUB_USERNAME`: Your GitHub username (required)
- `GITHUB_TOKEN`: Your GitHub personal access token (optional, recommended for better rate limits)
