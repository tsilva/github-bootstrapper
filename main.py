from dotenv import load_dotenv
load_dotenv()

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

def main() -> None:
    config = Config()
    
    if not config.is_valid:
        logger.error("Missing required environment variables: GITHUB_TOKEN and GITHUB_USERNAME")
        return
    
    username = os.getenv('GITHUB_USERNAME')
    if not username:
        logger.error("Error: GITHUB_USERNAME not set in .env file")
        sys.exit(1)
    
    base_path = get_base_path(username)
    
    # Ensure base directory exists
    os.makedirs(base_path, exist_ok=True)
    
    # Get all repositories
    try:
        repos = get_repos(username)
    except Exception as e:
        logger.error(f"Failed to fetch repositories: {e}")
        return
    
    # Process repositories in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {
            executor.submit(
                sync_repo, 
                repo['clone_url'], 
                repo['name'], 
                base_path
            ): repo['name'] 
            for repo in repos if not repo['fork']
        }
        
        for future in as_completed(future_to_repo):
            repo_name = future_to_repo[future]
            try:
                success = future.result()
                if success:
                    logger.info(f"Successfully processed {repo_name}")
            except Exception as e:
                logger.error(f"Error processing {repo_name}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
