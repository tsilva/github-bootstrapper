from github import Github
from dotenv import load_dotenv
import os
import sys
import logging
import requests
import subprocess
from typing import List, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_repos(username: str) -> List[Dict[str, Any]]:
    """Get all repositories for a given username."""
    url = f"https://api.github.com/users/{username}/repos"
    headers = {}
    
    # Use token if available for better rate limits
    if github_token := os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = f'token {github_token}'
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 403:
        logger.error("GitHub API rate limit exceeded. Consider adding GITHUB_TOKEN to .env")
        sys.exit(1)
    elif response.status_code != 200:
        raise Exception(f"Failed to get repositories: {response.status_code}")
    
    return response.json()

def has_unstaged_changes(repo_path: str) -> bool:
    """Check if repository has unstaged changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return True

def sync_repo(repo_url: str, repo_name: str, base_path: str) -> bool:
    """Sync a single repository."""
    repo_path = os.path.join(base_path, repo_name)
    
    if os.path.exists(repo_path):
        logger.info(f"Repository {repo_name} exists, checking status...")
        if has_unstaged_changes(repo_path):
            logger.warning(f"Skipping {repo_name} due to unstaged changes")
            return False
        
        logger.info(f"Pulling latest changes for {repo_name}")
        try:
            # First try to get the default branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            default_branch = result.stdout.strip()
            
            subprocess.run(
                ["git", "pull", "origin", default_branch],
                cwd=repo_path,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pull {repo_name}: {e}")
            return False
    else:
        logger.info(f"Cloning {repo_name}...")
        try:
            subprocess.run(
                ["git", "clone", repo_url, repo_path],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone {repo_name}: {e}")
            return False
    
    return True

def get_base_path(username: str) -> str:
    """Get the base path for repositories."""
    current_dir = Path(__file__).resolve().parent
    return str(current_dir.parent / "repos" / username)

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize GitHub client
    token = os.getenv('GITHUB_TOKEN')
    g = Github(token) if token else Github()
    
    # Get authenticated user
    user = g.get_user()
    print(f"Logged in as: {user.login}")
    
    # List all repositories
    for repo in user.get_repos():
        print(f"Repository: {repo.full_name}")
        print(f"- URL: {repo.html_url}")
        print(f"- Description: {repo.description}")
        print(f"- Stars: {repo.stargazers_count}")
        print("---")

if __name__ == "__main__":
    main()
