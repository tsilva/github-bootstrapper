# github-bootstrapper

A tool to automatically sync all your GitHub repositories.

## Setup

1. Install Miniconda if you haven't already:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
   bash miniconda.sh -b -p $HOME/miniconda
   ```

2. Create and activate the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate bootstrapper
   ```

3. Configure the .env file:
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub username and token
   ```

4. Run the script:
   ```bash
   python main.py
   ```

## Configuration

The `.env` file supports the following variables:
- `GITHUB_USERNAME`: Your GitHub username (required)
- `GITHUB_TOKEN`: Your GitHub personal access token (optional, recommended for better rate limits)
