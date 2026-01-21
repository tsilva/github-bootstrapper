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


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='github-bootstrapper',
        description='Multi-operation GitHub repository manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all repositories (clone + pull)
  github-bootstrapper sync

  # Clone only missing repositories
  github-bootstrapper clone-only --dry-run

  # Pull updates for existing repositories
  github-bootstrapper pull-only --workers 8

  # Execute Claude prompts using templates (forks/archived excluded by default)
  github-bootstrapper claude-exec init

  # Execute raw Claude prompts
  github-bootstrapper claude-exec "/readme-generator"

  # Enable sandbox mode for all repos
  github-bootstrapper sandbox-enable

  # Clean Claude settings
  github-bootstrapper settings-clean --mode analyze

  # Filter by organization
  github-bootstrapper sync --org mycompany --private-only

  # Filter by pattern
  github-bootstrapper readme-gen --pattern "my-*"
        """
    )

    # Global flags
    parser.add_argument(
        '--list-templates',
        action='store_true',
        help='List available prompt templates and exit'
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

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser.

    Args:
        parser: Parser to add arguments to
    """
    # Global configuration
    config_group = parser.add_argument_group('configuration')
    config_group.add_argument(
        '--repos-dir',
        help='Base directory for repositories (default: current directory, overrides REPOS_BASE_DIR)'
    )
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
            repos_dir=args.repos_dir,
            token=args.token,
            max_workers=args.workers,
            sequential=args.sequential
        )

        logger.info(f"Configuration loaded")
        logger.info(f"  Username: {config.github_username}")
        logger.info(f"  Base directory: {config.repos_base_dir}")
        logger.info(f"  Authenticated: {config.is_authenticated}")

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
