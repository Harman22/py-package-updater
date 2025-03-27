"""
Command-line interface for the package updater.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from .file_updater import FileUpdater
from .package_manager import PackageManager
from .test_discovery import TestDiscovery
from .update_tester import UpdateTester

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Automatically update Python packages while verifying tests pass.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all packages in the current directory
  python -m package_updater .
  
  # Update specific packages
  python -m package_updater . --packages requests pytest
  
  # Dry run without making changes
  python -m package_updater . --dry-run
  
  # Show more detailed output
  python -m package_updater . --verbose
""",
    )

    parser.add_argument("project_path", help="Path to the Python project directory")

    parser.add_argument(
        "--packages",
        nargs="+",
        help="Specific packages to update (default: all packages)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Run without making any changes"
    )

    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip running tests (not recommended)"
    )

    return parser


def validate_project_path(path: str) -> Optional[Path]:
    """Validate the project path and requirements files."""
    logger.info("Validating project path: %s", path)
    project_path = Path(path).resolve()

    if not project_path.exists():
        logger.error("Project path does not exist: %s", project_path)
        return None

    if not project_path.is_dir():
        logger.error("Project path is not a directory: %s", project_path)
        return None

    requirements = project_path / "requirements.txt"
    pipfile = project_path / "Pipfile"

    if not requirements.exists() and not pipfile.exists():
        logger.error("No requirements.txt or Pipfile found in %s", project_path)
        return None

    return project_path


def validate_tests(project_path: str) -> bool:
    """Validate that the project has runnable tests."""
    logger.info("Validating tests in the project")
    test_discovery = TestDiscovery(project_path)
    test_files = test_discovery.find_test_files()

    if not test_files:
        logger.warning("No test files found in the project")
        return False

    test_results = test_discovery.discover_and_validate_tests()
    valid_tests = any(result["valid"] for result in test_results.values())

    if not valid_tests:
        logger.error("No valid tests found in the project")
        return False

    logger.info("Found %s test files", len(test_files))
    for _, result in test_results.items():
        if result["valid"]:
            logger.debug("Valid test file: %s", result["relative_path"])
            logger.debug("Test functions: %s", ", ".join(result["test_functions"]))
        else:
            logger.warning("Invalid test file: %s", result["relative_path"])

    return True


def filter_updates(
    all_updates: Dict[str, str], selected_packages: Optional[list[str]] = None
) -> Dict[str, str]:
    """Filter updates to only include selected packages."""
    if not selected_packages:
        return all_updates

    return {
        pkg: version for pkg, version in all_updates.items() if pkg in selected_packages
    }


def validate_and_initialize(args) -> Optional[Path]:
    """Validate the project path and initialize components."""
    # Validate project path
    project_path = validate_project_path(args.project_path)
    if not project_path:
        return None

    # Validate tests if not skipping
    if not args.skip_tests and not validate_tests(str(project_path)):
        logger.warning("Proceeding with report generation despite no valid tests")

    return project_path


def analyze_updates(project_path: Path, args) -> Dict[str, str]:
    """Analyze package updates."""
    if not args.skip_tests:
        update_tester = UpdateTester(str(project_path))
        results = update_tester.update_all_packages()
    else:
        logger.warning("Skipping tests as requested")
        package_manager = PackageManager(str(project_path))
        results = {
            name: package_manager.get_latest_version(name)
            for name in package_manager.current_packages
        }

    updates = {}
    for pkg_name, status in results.items():
        if (
            status.compatible_version
            and status.compatible_version != status.current_version
        ):
            updates[pkg_name] = status.compatible_version

    # Filter updates if specific packages were requested
    if args.packages:
        updates = filter_updates(updates, args.packages)

    return updates


def apply_updates(project_path: Path, updates: Dict[str, str], args) -> None:
    """Apply updates to package files."""
    file_updater = FileUpdater(str(project_path))

    if not args.dry_run and updates:
        logger.info("Updating package files")
        update_results = file_updater.update_package_files(updates)

        for file_name, success in update_results.items():
            if success:
                logger.info("Successfully updated %s", file_name)
            else:
                logger.error("Failed to update %s", file_name)

    elif args.dry_run and updates:
        logger.info("Dry run - no files were modified")
        logger.info("The following updates are available:")
        for pkg, version in updates.items():
            logger.info("Package: %s, Recommended Version: %s", pkg, version)

    else:
        logger.info("No updates needed")


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the package updater."""
    logger.info("Starting package updater")
    parser = create_parser()
    args = parser.parse_args(args)

    # Setup logging
    setup_logging(args.verbose)
    logger.debug("Arguments: %s", args)

    # Validate project path
    project_path = validate_project_path(args.project_path)
    if not project_path:
        return 1

    try:
        # Validate and initialize
        project_path = validate_and_initialize(args)
        if not project_path:
            return 1

        # Analyze updates
        updates = analyze_updates(project_path, args)

        # Apply updates
        apply_updates(project_path, updates, args)

        return 0

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("An error occurred: %s", str(e))
        if args.verbose:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
