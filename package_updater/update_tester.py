"""
Module for coordinating and testing package updates.
"""

import logging
from typing import Dict, List, Optional, NamedTuple
from pathlib import Path
from datetime import datetime

from .package_manager import PackageManager
from .test_discovery import TestDiscovery
from .environment_manager import EnvironmentManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UpdateResult(NamedTuple):
    """Results of a package update attempt."""
    success: bool
    old_version: str
    new_version: str
    error_message: Optional[str] = None
    test_output: Optional[str] = None

class PackageUpdateStatus(NamedTuple):
    """Status of package updates."""
    package_name: str
    current_version: str
    target_version: str
    compatible_version: Optional[str]
    tested_versions: List[str]
    failed_versions: Dict[str, str]  # version -> error message

class UpdateTester:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.package_manager = PackageManager(project_path)
        self.test_discovery = TestDiscovery(project_path)
        self.env_manager = EnvironmentManager(project_path)
        
        # Create log directory
        self.log_dir = self.project_path / 'update_logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize logging file
        self.log_file = self.log_dir / f'update_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.file_handler = logging.FileHandler(self.log_file)
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(self.file_handler)

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
        except Exception as e:
            logger.error(f"Error setting up test environment: {str(e)}")
            return False

    def run_tests(self) -> tuple[bool, str]:
        """Run all discovered tests."""
        logger.info("Running tests")
        test_files = self.test_discovery.find_test_files()
        if not test_files:
            logger.warning("No test files found")
            return False, "No test files found"

        # Run pytest through the virtual environment
        success, output = self.env_manager.run_python_command(
            ['-m', 'pytest'] + test_files
        )
        return success, output

    def test_package_update(self, package_name: str, version: str) -> UpdateResult:
        """Test a specific package version update."""
        logger.info(f"Testing {package_name} version {version}")
        
        current_version = self.package_manager.current_packages.get(package_name)
        if not current_version:
            return UpdateResult(False, "unknown", version, 
                              f"Package {package_name} not found in current packages")

        try:
            # Install the new version
            if not self.env_manager.install_package(package_name, version):
                return UpdateResult(False, current_version, version,
                                  f"Failed to install {package_name}=={version}")

            # Run tests
            tests_passed, test_output = self.run_tests()
            if not tests_passed:
                return UpdateResult(False, current_version, version,
                                  "Tests failed", test_output)

            return UpdateResult(True, current_version, version,
                              test_output=test_output)

        except Exception as e:
            return UpdateResult(False, current_version, version,
                              f"Error during testing: {str(e)}")

    def find_compatible_update(self, package_name: str) -> PackageUpdateStatus:
        """Find the highest compatible version for a package."""
        logger.info(f"Finding compatible update for {package_name}")
        
        current_version = self.package_manager.current_packages.get(package_name)
        if not current_version:
            logger.error(f"Package {package_name} not found in current packages")
            return PackageUpdateStatus(
                package_name, "unknown", "unknown", None, [], {}
            )

        # Get available versions
        latest_version = self.package_manager.get_latest_version(package_name)
        if not latest_version:
            logger.error(f"Could not fetch latest version for {package_name}")
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
                logger.info(f"Found compatible version {version} for {package_name}")
            else:
                failed_versions[version] = result.error_message
                logger.warning(
                    f"Version {version} of {package_name} is not compatible: "
                    f"{result.error_message}"
                )

        return PackageUpdateStatus(
            package_name,
            current_version,
            latest_version,
            compatible_version,
            tested_versions,
            failed_versions
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
        logger.removeHandler(self.file_handler)
        self.file_handler.close() 