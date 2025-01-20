from dotenv import load_dotenv
load_dotenv()

import sys
import os
import logging
import requests
import subprocess
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_repos(username: str) -> List[Dict[str, Any]]:
    """Get all repositories for a given username."""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url)
    
    if response.status_code == 403:
        logger.error("GitHub API rate limit exceeded. Consider waiting or adding GITHUB_TOKEN")
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

def main():
    # Validate environment variables
    username = os.getenv('GITHUB_USERNAME')
    if not username:
        logger.error("GITHUB_USERNAME must be set in .env file")
        sys.exit(1)
    
    repos_dir = os.getenv('REPOS_BASE_DIR')
    if not repos_dir:
        logger.error("REPOS_BASE_DIR must be set in .env file")
        sys.exit(1)
    
    if not os.path.isdir(repos_dir):
        logger.error(f"REPOS_BASE_DIR '{repos_dir}' does not exist or is not a directory")
        sys.exit(1)
    
    # Fetch and process repositories
    repos = get_repos(username)
    for repo in repos:
        logger.info(f"Repository: {repo['full_name']}")
        logger.info(f"- URL: {repo['html_url']}")
        logger.info(f"- Description: {repo['description']}")
        logger.info("---")
        
        # Sync repository
        sync_repo(repo['clone_url'], repo['name'], repos_dir)

if __name__ == "__main__":
    main()
