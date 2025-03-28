"""
Module for managing virtual environments and package installations.
"""

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import virtualenv

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Class for managing virtual environments and package installations."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.venv_path = self.project_path / ".venv"
        self.python_path = self.venv_path / (
            "Scripts" if sys.platform == "win32" else "bin"
        )
        self.pip_path = self.python_path / (
            "pip.exe" if sys.platform == "win32" else "pip"
        )
        self.python_executable = self.python_path / (
            "python.exe" if sys.platform == "win32" else "python"
        )

    def create_virtual_environment(self) -> bool:
        """Create a new virtual environment."""
        logger.debug("Creating virtual environment")
        try:
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
            virtualenv.cli_run([str(self.venv_path)], setup_logging=False)
            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error creating virtual environment: %s", str(e))
            return False

    def run_pip_command(self, command: List[str]) -> tuple[bool, str]:
        """Run a pip command in the virtual environment."""
        logger.debug("Running pip command: %s", str(command))
        try:
            result = subprocess.run(
                [str(self.pip_path)] + command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:  # pylint: disable=broad-exception-caught
            return False, str(e)

    def install_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Install a specific package version."""
        logger.debug("Installing package: %s==%s", package_name, version)
        package_spec = f"{package_name}=={version}" if version else package_name
        success, output = self.run_pip_command(["install", package_spec])
        if not success:
            logger.error("Failed to install %s: %s", package_spec, output)
        return success

    def install_requirements(self, requirements: Dict[str, str]) -> bool:
        """Install all packages from the requirements dictionary."""
        logger.info("Installing all packges from requirements")
        temp_requirements = self.venv_path / "temp_requirements.txt"
        try:
            # Create temporary requirements file
            with open(temp_requirements, "w", encoding="utf-8") as f:
                for package, version in requirements.items():
                    if version:
                        f.write(f"{package}=={version}\n")
                    else:
                        f.write(f"{package}\n")

            # Install requirements
            success, output = self.run_pip_command(
                ["install", "-r", str(temp_requirements)]
            )
            if not success:
                logger.error("Failed to install requirements: %s", output)
            return success
        finally:
            # Clean up temporary file
            if temp_requirements.exists():
                temp_requirements.unlink()

    def get_installed_packages(self) -> Dict[str, str]:
        """Get a dictionary of installed packages and their versions."""
        logger.debug("Getting installed packages")
        success, output = self.run_pip_command(["list", "--format=json"])
        if not success:
            return {}

        try:
            packages = json.loads(output)
            return {pkg["name"]: pkg["version"] for pkg in packages}
        except json.JSONDecodeError:
            return {}

    def verify_installation(self, requirements: Dict[str, str]) -> bool:
        """Verify that all required packages are installed with correct versions."""
        logger.debug("Verifying package installation")
        installed = self.get_installed_packages()
        for package, version in requirements.items():
            if package.lower() not in {k.lower() for k in installed.keys()}:
                logger.debug("Package %s is not installed", package)
                return False
            if version and installed[package.lower()] != version:
                logger.debug(
                    "Package %s version mismatch: expected %s got %s",
                    package,
                    version,
                    installed[package],
                )
                return False
        return True

    def run_python_command(self, command: List[str]) -> tuple[bool, str]:
        """Run a Python command in the virtual environment."""
        try:
            result = subprocess.run(
                [str(self.python_executable)] + command,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_path,
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:  # pylint: disable=broad-exception-caught
            return False, str(e)

    def cleanup(self):
        """Clean up the virtual environment."""
        try:
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error cleaning up virtual environment: %s", str(e))
