"""
Command-line interface for the package updater.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict

from .package_manager import PackageManager
from .test_discovery import TestDiscovery
from .update_tester import UpdateTester
from .report_generator import ReportGenerator
from .file_updater import FileUpdater

def setup_logging(verbose: bool = False):
    """Configure logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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
"""
    )

    parser.add_argument(
        "project_path",
        help="Path to the Python project directory"
    )
    
    parser.add_argument(
        "--packages",
        nargs="+",
        help="Specific packages to update (default: all packages)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making any changes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (not recommended)"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate a report without updating files"
    )

    return parser

def validate_project_path(path: str) -> Optional[Path]:
    """Validate the project path and requirements files."""
    project_path = Path(path).resolve()
    
    if not project_path.exists():
        logging.error(f"Project path does not exist: {project_path}")
        return None
        
    if not project_path.is_dir():
        logging.error(f"Project path is not a directory: {project_path}")
        return None
        
    requirements = project_path / "requirements.txt"
    pipfile = project_path / "Pipfile"
    
    if not requirements.exists() and not pipfile.exists():
        logging.error(
            f"No requirements.txt or Pipfile found in {project_path}"
        )
        return None
        
    return project_path

def validate_tests(project_path: str) -> bool:
    """Validate that the project has runnable tests."""
    test_discovery = TestDiscovery(project_path)
    test_files = test_discovery.find_test_files()
    
    if not test_files:
        logging.warning("No test files found in the project")
        return False
    
    test_results = test_discovery.discover_and_validate_tests()
    valid_tests = any(result['valid'] for result in test_results.values())
    
    if not valid_tests:
        logging.error("No valid tests found in the project")
        return False
    
    logging.info(f"Found {len(test_files)} test files")
    for test_file, result in test_results.items():
        if result['valid']:
            logging.debug(f"Valid test file: {result['relative_path']}")
            logging.debug(f"Test functions: {', '.join(result['test_functions'])}")
        else:
            logging.warning(f"Invalid test file: {result['relative_path']}")
    
    return True

def filter_updates(
    all_updates: Dict[str, str],
    selected_packages: Optional[list[str]] = None
) -> Dict[str, str]:
    """Filter updates to only include selected packages."""
    if not selected_packages:
        return all_updates
        
    return {
        pkg: version
        for pkg, version in all_updates.items()
        if pkg in selected_packages
    }

def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the package updater."""
    parser = create_parser()
    args = parser.parse_args(args)
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Validate project path
    project_path = validate_project_path(args.project_path)
    if not project_path:
        return 1
    
    try:
        # Validate tests if not skipping
        if not args.skip_tests:
            if not validate_tests(str(project_path)):
                if not args.report_only:
                    logging.error("Cannot proceed without valid tests")
                    return 1
                logging.warning("Proceeding with report generation despite no valid tests")
        
        # Initialize components
        update_tester = UpdateTester(str(project_path))
        report_generator = ReportGenerator(str(project_path))
        file_updater = FileUpdater(str(project_path))
        
        logging.info("Starting package update analysis")
        
        # Run update testing
        if not args.skip_tests:
            results = update_tester.update_all_packages()
        else:
            logging.warning("Skipping tests as requested")
            package_manager = PackageManager(str(project_path))
            results = {
                name: package_manager.get_latest_version(name)
                for name in package_manager.current_packages
            }
        
        # Generate updates dictionary
        updates = {}
        for pkg_name, status in results.items():
            if status.compatible_version and status.compatible_version != status.current_version:
                updates[pkg_name] = status.compatible_version
        
        # Filter updates if specific packages were requested
        if args.packages:
            updates = filter_updates(updates, args.packages)
        
        # Generate and save report
        report_file = report_generator.generate_and_save_report(results)
        logging.info(f"Report generated: {report_file}")
        
        # Update package files if not in dry-run mode
        if not args.dry_run and not args.report_only and updates:
            logging.info("Updating package files")
            update_results = file_updater.update_package_files(updates)
            
            for file_name, success in update_results.items():
                if success:
                    logging.info(f"Successfully updated {file_name}")
                else:
                    logging.error(f"Failed to update {file_name}")
        elif args.dry_run:
            logging.info("Dry run - no files were modified")
        elif args.report_only:
            logging.info("Report only - no files were modified")
        else:
            logging.info("No updates needed")
        
        return 0
        
    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        if args.verbose:
            logging.exception("Detailed error information:")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 