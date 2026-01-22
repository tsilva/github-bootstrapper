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
from .core.repo_manager import RepoManager
from .operations.registry import registry
from .utils.filters import RepoFilter
from .utils.progress import print_summary
from .pipelines import pipeline_registry, PipelineExecutor


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

  # Execute Claude prompts using templates (forks/archived excluded by default)
  gitfleet claude-exec init

  # Execute raw Claude prompts
  gitfleet claude-exec "/readme-generator"

  # Enable sandbox mode for all repos
  gitfleet sandbox-enable

  # Clean Claude settings
  gitfleet settings-clean --mode analyze

  # Use skill pipelines (new)
  gitfleet pipeline claude-settings-optimizer --mode analyze
  gitfleet pipeline readme-generator
  gitfleet pipeline logo-generator

  # Skill pipelines with conditions (Claude evaluates)
  gitfleet pipeline readme-generator --condition "README tagline does NOT contain an emoji"

  # Filter by organization
  gitfleet sync --org mycompany --private-only

  # Filter by pattern
  gitfleet readme-gen --pattern "my-*"
        """
    )

    # Global flags
    parser.add_argument(
        '--list-templates',
        action='store_true',
        help='List available prompt templates and exit'
    )
    parser.add_argument(
        '--list-pipelines',
        action='store_true',
        help='List available pipelines and exit'
    )

    # Subcommands (operations)
    subparsers = parser.add_subparsers(
        dest='operation',
        help='Operation to perform',
        required=False
    )

    # Dynamically add subcommands from registry
    for op_name, op_class in registry.get_all_operations().items():
        op_parser = subparsers.add_parser(
            op_name,
            help=op_class.description
        )
        _add_common_args(op_parser)

        # Add operation-specific arguments
        if op_name == 'claude-exec':
            op_parser.add_argument(
                'prompt',
                help='Template name or raw prompt string'
            )
            op_parser.add_argument(
                '--force',
                action='store_true',
                help='Execute on all repos, ignoring template should_run() logic'
            )
            op_parser.add_argument(
                '--yes', '-y',
                action='store_true',
                help='Skip confirmation prompt'
            )
        elif op_name == 'readme-gen':
            op_parser.add_argument(
                '--force',
                action='store_true',
                help='Regenerate README even if it already exists'
            )
        elif op_name == 'claude-init':
            op_parser.add_argument(
                '--force',
                action='store_true',
                help='Regenerate CLAUDE.md even if it already exists'
            )
        elif op_name == 'settings-clean':
            op_parser.add_argument(
                '--mode',
                choices=['analyze', 'clean', 'auto-fix'],
                default='analyze',
                help='Operation mode (default: analyze)'
            )

    # Add pipeline subcommand
    pipeline_parser = subparsers.add_parser(
        'pipeline',
        help='Execute a pipeline (new composable architecture)'
    )
    _add_common_args(pipeline_parser)
    pipeline_parser.add_argument(
        'pipeline_name',
        help='Name of the pipeline to execute'
    )
    pipeline_parser.add_argument(
        '--force',
        action='store_true',
        help='Force execution, ignoring pipeline predicates'
    )
    pipeline_parser.add_argument(
        '--condition',
        metavar='CONDITION',
        help='Natural language condition for Claude to evaluate (for skill pipelines)'
    )
    pipeline_parser.add_argument(
        '--mode',
        choices=['analyze', 'clean', 'auto-fix'],
        default='analyze',
        help='Operation mode for settings-optimizer/settings-clean (default: analyze)'
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
    pipeline_name = args.pipeline_name

    # Get pipeline class
    pipeline_class = pipeline_registry.get(pipeline_name)
    if not pipeline_class:
        available = ', '.join(pipeline_registry.list_pipelines())
        logger.error(f"Unknown pipeline: {pipeline_name}. Available: {available}")
        return 1

    # Build pipeline kwargs based on pipeline type
    pipeline_kwargs = {}

    # Skill pipelines that support --condition
    condition_pipelines = ['readme-generator', 'logo-generator', 'name-generator']
    if pipeline_name in condition_pipelines:
        condition = getattr(args, 'condition', None)
        if condition:
            pipeline_kwargs['condition'] = condition

    # Pipelines that support --mode
    mode_pipelines = ['claude-settings-optimizer', 'settings-clean']
    if pipeline_name in mode_pipelines:
        mode = getattr(args, 'mode', 'analyze')
        pipeline_kwargs['mode'] = mode

    # Create pipeline instance
    pipeline = pipeline_class(**pipeline_kwargs)

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
        force=getattr(args, 'force', False)
    )

    # Print summary
    print_summary(results, operation_name=f"pipeline:{pipeline_name}")

    # Return exit code based on failures
    failed_count = sum(1 for r in results if r.failed)
    return 1 if failed_count > 0 else 0


def main():
    """Main entry point."""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()

    # Handle --list-templates flag
    if args.list_templates:
        from .prompt_templates import template_registry
        print("Available prompt templates:")
        for name, template_class in template_registry.get_all_templates().items():
            print(f"  {name}: {template_class.description}")
        return 0

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

        # Apply filters
        repo_filter = RepoFilter(
            repo_names=args.repos,
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

        # Handle pipeline command separately
        if args.operation == 'pipeline':
            return _execute_pipeline(
                args, config, github_client, repos, logger
            )

        # Get operation class
        operation_class = registry.get(args.operation)

        # Use operation's default workers if user didn't specify
        if args.workers is None and operation_class.default_workers is not None:
            config.max_workers = operation_class.default_workers
            logger.info(f"  Using operation default workers: {config.max_workers}")

        # Check if operation requires token
        if operation_class.requires_token and not config.is_authenticated:
            logger.error(
                f"Operation '{args.operation}' requires a GitHub token. "
                "Set GITHUB_TOKEN in .env or use --token"
            )
            return 1

        # Create repository manager
        repo_manager = RepoManager(
            github_client=github_client,
            base_dir=config.repos_base_dir,
            max_workers=config.max_workers,
            sequential=config.sequential
        )

        # Build operation-specific kwargs
        operation_kwargs = {'clone_url_getter': github_client.get_clone_url}

        # Add operation-specific arguments
        if args.operation == 'claude-exec':
            operation_kwargs['prompt'] = args.prompt
            operation_kwargs['force'] = getattr(args, 'force', False)
            operation_kwargs['yes'] = getattr(args, 'yes', False)
        elif args.operation == 'readme-gen':
            operation_kwargs['force'] = getattr(args, 'force', False)
        elif args.operation == 'claude-init':
            operation_kwargs['force'] = getattr(args, 'force', False)
        elif args.operation == 'settings-clean':
            operation_kwargs['mode'] = getattr(args, 'mode', 'analyze')

        # Execute operation
        results = repo_manager.execute_operation(
            operation_class=operation_class,
            repos=repos,
            dry_run=args.dry_run,
            **operation_kwargs
        )

        # Print summary
        print_summary(results, operation_name=args.operation)

        # Return exit code based on failures
        failed_count = sum(1 for r in results if r.failed)
        return 1 if failed_count > 0 else 0

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
