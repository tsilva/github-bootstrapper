from dotenv import load_dotenv
load_dotenv()

import sys
import os
import logging
import requests
import subprocess
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_user_orgs(username: str, headers: dict) -> List[str]:
    """Get all organizations for a user."""
    url = f"https://api.github.com/users/{username}/orgs"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [org['login'] for org in response.json()]
    return []

def get_org_repos(org: str, headers: dict) -> List[Dict[str, Any]]:
    """Get all repositories for an organization."""
    all_repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?page={page}&per_page={per_page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Failed to get repositories for org {org}: {response.status_code}")
            break
        
        repos_page = response.json()
        if not repos_page:
            break
            
        all_repos.extend(repos_page)
        page += 1
    
    return all_repos

def get_repos(username: str) -> List[Dict[str, Any]]:
    """Get all repositories for a given username, including org repos."""
    headers = {}
    if token := os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = f'token {token}'
        logger.info("Using GitHub token for authentication")
        # When authenticated, use different endpoint to get ALL repos including private ones
        url_template = "https://api.github.com/user/repos?page={}&per_page={}&affiliation=owner,collaborator,organization_member"
    else:
        # Unauthenticated - only public repos
        url_template = f"https://api.github.com/users/{username}/repos?page={{}}&per_page={{}}"

    # Get repos using selected endpoint
    all_repos = []
    page = 1
    per_page = 100

    while True:
        url = url_template.format(page, per_page)
        response = requests.get(url, headers=headers)
        
        if response.status_code == 403:
            logger.error("GitHub API rate limit exceeded")
            sys.exit(1)
        elif response.status_code != 200:
            raise Exception(f"Failed to get repositories: {response.status_code}")
        
        repos_page = response.json()
        if not repos_page:
            break
            
        all_repos.extend(repos_page)
        page += 1

    # No need to fetch org repos separately when using authenticated endpoint
    if not headers:
        # Only fetch org repos if not authenticated
        orgs = get_user_orgs(username, headers)
        logger.info(f"Found {len(orgs)} organizations")
        
        for org in orgs:
            org_repos = get_org_repos(org, headers)
            logger.info(f"Found {len(org_repos)} repositories in organization {org}")
            all_repos.extend(org_repos)

    # Deduplicate repos based on id
    unique_repos = {repo['id']: repo for repo in all_repos}.values()
    logger.info(f"Found {len(unique_repos)} unique repositories total")
    return list(unique_repos)

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

def get_clone_url(repo: Dict[str, Any]) -> str:
    """Get the appropriate clone URL based on token availability."""
    if token := os.getenv('GITHUB_TOKEN'):
        # Use HTTPS URL with token for authentication
        base_url = repo['clone_url'].replace('https://', '')
        return f'https://{token}@{base_url}'
    return repo['clone_url']

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

def process_repo(repo: Dict[str, Any], repos_dir: str) -> Tuple[str, bool]:
    """Process a single repository and return its name and success status."""
    name = repo['name']
    logger.info(f"Repository: {repo['full_name']}")
    logger.info(f"- URL: {repo['html_url']}")
    logger.info(f"- Private: {repo['private']}")
    logger.info(f"- Description: {repo['description']}")
    logger.info("---")
    
    success = sync_repo(get_clone_url(repo), name, repos_dir)
    return name, success

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
    
    # Fetch repositories
    repos = get_repos(username)
    
    # Determine processing mode based on token availability
    if token := os.getenv('GITHUB_TOKEN'):
        # Parallel processing with token
        max_workers = multiprocessing.cpu_count()
        logger.info(f"Using parallel processing with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_repo = {
                executor.submit(process_repo, repo, repos_dir): repo
                for repo in repos
            }
            
            # Process completed tasks
            for future in as_completed(future_to_repo):
                repo_name, success = future.result()
                status = "Successfully processed" if success else "Failed to process"
                logger.info(f"{status} repository: {repo_name}")
    else:
        # Sequential processing without token
        logger.info("Using sequential processing (no token available)")
        for repo in repos:
            process_repo(repo, repos_dir)

if __name__ == "__main__":
    main()
