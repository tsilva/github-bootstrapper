"""Main entry point for GitHub Bootstrapper CLI."""

from dotenv import load_dotenv
load_dotenv()

import sys
import argparse
import logging
from typing import List, Optional

from .config import Config
from .core.logger import setup_logging
from .core.github_client import GitHubClient
from .utils.filters import RepoFilter
from .utils.progress import print_summary
from .pipelines import pipeline_registry, PipelineExecutor


def _read_stdin_repos() -> List[str]:
    """Read repository names from stdin if piped.

    Returns:
        List of repo names from stdin, or empty list if stdin is a tty
    """
    if sys.stdin.isatty():
        return []

    repos = []
    for line in sys.stdin:
        line = line.strip()
        if line:  # Skip empty lines
            repos.append(line)
    return repos


def _scan_local_git_repos(base_dir: str) -> List[str]:
    """Scan a directory for subdirectories that are git repositories.

    Args:
        base_dir: Directory to scan

    Returns:
        List of directory names that are git repositories
    """
    import os

    repos = []
    try:
        for entry in os.scandir(base_dir):
            if entry.is_dir() and not entry.name.startswith('.'):
                git_dir = os.path.join(entry.path, '.git')
                if os.path.isdir(git_dir):
                    repos.append(entry.name)
    except OSError:
        pass
    return sorted(repos)


def is_inside_git_repo(path: str) -> bool:
    """Check if a path is inside a git repository.

    Args:
        path: Directory path to check

    Returns:
        True if the path is inside a git repository, False otherwise
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except FileNotFoundError:
        return False


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='gitfleet',
        description='Multi-operation GitHub repository manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all repositories (clone + pull)
  gitfleet sync

  # Clone only missing repositories
  gitfleet clone-only --dry-run

  # Pull updates for existing repositories
  gitfleet pull-only --workers 8

  # Check repository status
  gitfleet status

  # Execute Claude prompts (raw prompts or skills)
  gitfleet claude-exec "/readme-generator" --repo my-repo
  gitfleet claude-exec "Add a LICENSE file" --dry-run

  # Enable sandbox mode for all repos
  gitfleet sandbox-enable

  # Clean Claude settings
  gitfleet settings-clean --mode analyze

  # Filter by organization
  gitfleet sync --org mycompany --private-only

  # Filter by pattern
  gitfleet sync --pattern "my-*"

  # Pipe repo names from other commands
  ls sandbox-* | gitfleet claude-exec "Add a LICENSE file"
  echo -e "repo1\\nrepo2" | gitfleet sync
        """
    )

    # Global flags
    parser.add_argument(
        '--list-pipelines',
        action='store_true',
        help='List available pipelines and exit'
    )

    # Subcommands (pipelines)
    subparsers = parser.add_subparsers(
        dest='operation',
        help='Operation to perform',
        required=False
    )

    # Dynamically add subcommands from pipeline registry
    for pipeline_name in pipeline_registry.list_pipelines():
        pipeline_class = pipeline_registry.get(pipeline_name)
        desc = getattr(pipeline_class, 'description', 'No description')

        op_parser = subparsers.add_parser(
            pipeline_name,
            help=desc
        )
        _add_common_args(op_parser)

        # Add pipeline-specific arguments
        if pipeline_name == 'claude-exec':
            op_parser.add_argument(
                'prompt',
                help='Prompt string or skill name (e.g., "/readme-generator")'
            )
            op_parser.add_argument(
                '--force',
                action='store_true',
                help='Execute on all repos, ignoring pipeline predicates'
            )
            op_parser.add_argument(
                '--yes', '-y',
                action='store_true',
                help='Skip confirmation prompt'
            )
        elif pipeline_name == 'settings-clean':
            op_parser.add_argument(
                '--mode',
                choices=['analyze', 'clean', 'auto-fix'],
                default='analyze',
                help='Operation mode (default: analyze)'
            )
        elif pipeline_name in ('sync', 'clone-only', 'pull-only', 'sandbox-enable', 'description-sync', 'status', 'commit-push'):
            op_parser.add_argument(
                '--force',
                action='store_true',
                help='Force execution, ignoring pipeline predicates'
            )
            op_parser.add_argument(
                '--yes', '-y',
                action='store_true',
                help='Skip confirmation prompt'
            )
            # Commit-push specific arguments
            if pipeline_name == 'commit-push':
                op_parser.add_argument(
                    '--message', '-m',
                    help='Commit message'
                )

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser.

    Args:
        parser: Parser to add arguments to
    """
    # Global configuration
    config_group = parser.add_argument_group('configuration')
    config_group.add_argument(
        '--username',
        help='GitHub username (overrides GITHUB_USERNAME)'
    )
    config_group.add_argument(
        '--token',
        help='GitHub token (overrides GITHUB_TOKEN)'
    )

    # Execution control
    exec_group = parser.add_argument_group('execution control')
    exec_group.add_argument(
        '--workers',
        type=int,
        metavar='N',
        help='Number of parallel workers (default: CPU count)'
    )
    exec_group.add_argument(
        '--sequential',
        action='store_true',
        help='Force sequential processing (no parallelization)'
    )
    exec_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without executing'
    )

    # Repository filtering
    filter_group = parser.add_argument_group('repository filtering')
    filter_group.add_argument(
        '--repo',
        action='append',
        dest='repos',
        metavar='NAME',
        help='Target specific repository (can be repeated)'
    )
    filter_group.add_argument(
        '--org',
        action='append',
        dest='orgs',
        metavar='NAME',
        help='Filter by organization (can be repeated)'
    )
    filter_group.add_argument(
        '--pattern',
        metavar='GLOB',
        help='Filter by name pattern (e.g., "my-*")'
    )
    filter_group.add_argument(
        '--include-forks',
        action='store_true',
        help='Include forked repositories (excluded by default)'
    )
    filter_group.add_argument(
        '--include-archived',
        action='store_true',
        help='Include archived repositories (excluded by default)'
    )
    filter_group.add_argument(
        '--private-only',
        action='store_true',
        help='Only include private repositories'
    )
    filter_group.add_argument(
        '--public-only',
        action='store_true',
        help='Only include public repositories'
    )


def _execute_pipeline(args, config, github_client, repos, logger):
    """Execute a pipeline.

    Args:
        args: Parsed command line arguments
        config: Configuration object
        github_client: GitHub client
        repos: List of repositories
        logger: Logger instance

    Returns:
        Exit code
    """
    pipeline_name = args.operation

    # Get pipeline class
    pipeline_class = pipeline_registry.get(pipeline_name)
    if not pipeline_class:
        available = ', '.join(pipeline_registry.list_pipelines())
        logger.error(f"Unknown pipeline: {pipeline_name}. Available: {available}")
        return 1

    # Build pipeline kwargs based on pipeline type
    pipeline_kwargs = {}

    # Claude pipeline requires a prompt
    if pipeline_name == 'claude-exec':
        prompt = getattr(args, 'prompt', None)
        if not prompt:
            logger.error("The claude-exec pipeline requires a prompt argument")
            return 1
        pipeline_kwargs['prompt'] = prompt

    # Pipelines that support --mode
    if pipeline_name == 'settings-clean':
        mode = getattr(args, 'mode', 'analyze')
        pipeline_kwargs['mode'] = mode

    # Commit-push pipeline supports --message
    if pipeline_name == 'commit-push':
        message = getattr(args, 'message', None)
        if message:
            pipeline_kwargs['message'] = message

    # Create pipeline instance
    pipeline = pipeline_class(**pipeline_kwargs)

    # Use pipeline's default workers if user didn't specify
    if args.workers is None and pipeline.default_workers is not None:
        config.max_workers = pipeline.default_workers
        logger.info(f"  Using pipeline default workers: {config.max_workers}")

    # Check if pipeline requires token
    if pipeline.requires_token and not config.is_authenticated:
        logger.error(
            f"Pipeline '{pipeline_name}' requires a GitHub token. "
            "Set GITHUB_TOKEN in .env or use --token"
        )
        return 1

    # Create pipeline executor
    executor = PipelineExecutor(
        base_dir=config.repos_base_dir,
        max_workers=config.max_workers,
        sequential=config.sequential or not pipeline.safe_parallel,
        clone_url_getter=github_client.get_clone_url
    )

    # Execute pipeline
    results = executor.execute(
        pipeline=pipeline,
        repos=repos,
        dry_run=args.dry_run,
        force=getattr(args, 'force', False),
        yes=getattr(args, 'yes', False)
    )

    # Print summary
    print_summary(results, operation_name=pipeline_name)

    # Return exit code based on failures
    failed_count = sum(1 for r in results if r.failed)
    return 1 if failed_count > 0 else 0


def main():
    """Main entry point."""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()

    # Handle --list-pipelines flag
    if args.list_pipelines:
        print("Available pipelines:")
        for name in pipeline_registry.list_pipelines():
            pipeline_class = pipeline_registry.get(name)
            # Get description from class attribute
            desc = getattr(pipeline_class, 'description', 'No description')
            print(f"  {name}: {desc}")
        return 0

    # Check if operation is provided
    if not args.operation:
        parser.print_help()
        return 1

    # Setup logging
    logger = setup_logging(operation=args.operation)

    try:
        # Load configuration
        config = Config.from_env_and_args(
            username=args.username,
            token=args.token,
            max_workers=args.workers,
            sequential=args.sequential
        )

        logger.info(f"Configuration loaded")
        logger.info(f"  Username: {config.github_username}")
        logger.info(f"  Base directory: {config.repos_base_dir}")
        logger.info(f"  Authenticated: {config.is_authenticated}")

        # Check if running from inside a git repository
        repos_dir = config.repos_base_dir
        if is_inside_git_repo(repos_dir):
            logger.error(
                f"Cannot run from inside a git repository: {repos_dir}\n"
                "Please run from a parent directory containing your repositories."
            )
            return 1

        # Create GitHub client
        github_client = GitHubClient(
            username=config.github_username,
            token=config.github_token
        )

        # Fetch repositories
        logger.info("Fetching repositories from GitHub...")
        repos = github_client.get_repos()

        # Read repos from stdin if piped
        stdin_repos = _read_stdin_repos()

        # Merge stdin repos with CLI --repo args
        all_repos = (args.repos or []) + stdin_repos

        # If no repos specified, scan local git repos
        if not all_repos:
            all_repos = _scan_local_git_repos(config.repos_base_dir)
            if all_repos:
                logger.info(f"Found {len(all_repos)} local git repositories")

        repo_names = all_repos if all_repos else None

        # Apply filters
        repo_filter = RepoFilter(
            repo_names=repo_names,
            org_names=args.orgs,
            patterns=[args.pattern] if args.pattern else None,
            include_forks=args.include_forks,
            include_archived=args.include_archived,
            private_only=args.private_only,
            public_only=args.public_only
        )

        if repo_filter.has_filters:
            logger.info("Applying repository filters...")
            repos = repo_filter.filter(repos)

        if not repos:
            logger.warning("No repositories match the filter criteria")
            return 0

        # Execute pipeline
        return _execute_pipeline(args, config, github_client, repos, logger)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
