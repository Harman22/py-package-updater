"""
Module for coordinating and testing package updates.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .environment_manager import EnvironmentManager
from .package_manager import PackageManager
from .test_discovery import TestDiscovery

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Results of a package update attempt."""

    success: bool
    error_message: Optional[str] = None


@dataclass
class PackageUpdateStatus:
    """Status of package updates."""

    package_name: str
    current_version: str
    target_version: str
    compatible_version: Optional[str]
    tested_versions: List[str]
    failed_versions: Dict[str, str]  # version -> error message


class UpdateTester:
    """Class for coordinating and testing package updates."""

    def __init__(self, project_path: str, test_folder: Optional[str] = None):
        self.project_path = Path(project_path)
        self.package_manager = PackageManager(project_path)
        self.test_discovery = TestDiscovery(project_path, test_folder)
        self.env_manager = EnvironmentManager(project_path)

        # Verify packages were initialized
        if not self.package_manager.current_packages:
            logger.error("No packages found to update")
            raise ValueError("No packages found in requirements.txt or Pipfile")

    def setup_test_environment(self) -> bool:
        """Set up initial test environment with current package versions."""
        logger.info("Setting up test environment")

        try:
            # Create fresh virtual environment
            if not self.env_manager.create_virtual_environment():
                logger.error("Failed to create virtual environment")
                return False

            # Install current package versions
            current_packages = self.package_manager.current_packages
            if not self.env_manager.install_requirements(current_packages):
                logger.error("Failed to install current package versions")
                return False

            # Verify installation
            if not self.env_manager.verify_installation(current_packages):
                logger.error("Failed to verify package installation")
                return False

            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error setting up test environment: %s", str(e))
            return False

    def run_tests(self) -> tuple[bool, str]:
        """Run all discovered tests."""
        logger.info("Running tests")
        test_files = self.test_discovery.find_test_files()
        if not test_files:
            logger.warning("No test files found")
            return False, "No test files found"

        # Convert test files to relative paths
        relative_test_files = [
            os.path.relpath(f, str(self.project_path)) for f in test_files
        ]

        logger.debug("Running tests: %s", relative_test_files)
        # Run pytest with common options
        pytest_command = [
            "-m",
            "pytest",
            "-v",  # verbose output
        ] + relative_test_files

        success, output = self.env_manager.run_python_command(pytest_command)
        logger.debug("Test result: success=%s, output %s", success, output)

        return success, output

    def test_package_update(self, package_name: str, version: str) -> UpdateResult:
        """Test a specific package version update."""
        logger.info("Testing %s version %s", package_name, version)

        current_version = self.package_manager.current_packages.get(package_name)
        if not current_version:
            return UpdateResult(
                False,
                f"Package {package_name} not found in current packages",
            )

        try:
            # Install the new version
            if not self.env_manager.install_package(package_name, version):
                return UpdateResult(
                    False,
                    f"Failed to install {package_name}=={version}",
                )

            # Run tests
            tests_passed, test_output = self.run_tests()
            if not tests_passed:
                return UpdateResult(False, f"Tests failed: {test_output}")

            return UpdateResult(True)

        except Exception as e:  # pylint: disable=broad-exception-caught
            return UpdateResult(False, f"Error during testing: {str(e)}")

    def find_compatible_update(self, package_name: str) -> PackageUpdateStatus:
        """Find the highest compatible version for a package."""
        logger.info("Finding compatible update for %s", package_name)

        current_version = self.package_manager.current_packages.get(package_name)
        if not current_version:
            logger.error("Package %s not found in current packages", package_name)
            return PackageUpdateStatus(package_name, "unknown", "unknown", None, [], {})

        # Get available versions
        latest_version = self.package_manager.get_latest_version(package_name)
        if not latest_version:
            logger.error("Could not fetch latest version for %s", package_name)
            return PackageUpdateStatus(
                package_name, current_version, "unknown", None, [], {}
            )

        versions = self.package_manager.get_version_range(
            package_name, current_version, latest_version
        )

        tested_versions = []
        failed_versions = {}
        compatible_version = None

        # Test each version in ascending order
        for version in versions:
            if version == current_version:
                continue

            # Reset environment to current versions before testing new version
            self.setup_test_environment()

            result = self.test_package_update(package_name, version)
            tested_versions.append(version)

            if result.success:
                compatible_version = version
                logger.info("Found compatible version %s for %s", version, package_name)
            else:
                failed_versions[version] = result.error_message
                logger.warning(
                    "Version %s of %s is not compatible: %s",
                    version,
                    package_name,
                    result.error_message,
                )

        return PackageUpdateStatus(
            package_name,
            current_version,
            latest_version,
            compatible_version,
            tested_versions,
            failed_versions,
        )

    def update_all_packages(self) -> Dict[str, PackageUpdateStatus]:
        """Test updates for all packages and return results."""
        logger.info("Starting update testing for all packages")

        if not self.setup_test_environment():
            logger.error("Failed to set up initial test environment")
            return {}

        results = {}
        for package_name in self.package_manager.current_packages:
            results[package_name] = self.find_compatible_update(package_name)

        return results

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources")
        self.env_manager.cleanup()
