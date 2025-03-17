"""
Module for managing virtual environments and package installations.
"""

import os
import sys
import shutil
import subprocess
import venv
from typing import Dict, List, Optional
from pathlib import Path

class EnvironmentManager:
    def __init__(self, project_path: str, venv_path: Optional[str] = None):
        self.project_path = Path(project_path)
        self.venv_path = Path(venv_path) if venv_path else self.project_path / '.venv'
        self.python_path = self.venv_path / ('Scripts' if sys.platform == 'win32' else 'bin')
        self.pip_path = self.python_path / ('pip.exe' if sys.platform == 'win32' else 'pip')
        self.python_executable = self.python_path / ('python.exe' if sys.platform == 'win32' else 'python')

    def create_virtual_environment(self) -> bool:
        """Create a new virtual environment."""
        try:
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
            
            venv.create(self.venv_path, with_pip=True)
            return True
        except Exception as e:
            print(f"Error creating virtual environment: {str(e)}")
            return False

    def run_pip_command(self, command: List[str]) -> tuple[bool, str]:
        """Run a pip command in the virtual environment."""
        try:
            result = subprocess.run(
                [str(self.pip_path)] + command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)

    def install_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Install a specific package version."""
        package_spec = f"{package_name}=={version}" if version else package_name
        success, output = self.run_pip_command(['install', package_spec])
        if not success:
            print(f"Failed to install {package_spec}: {output}")
        return success

    def install_requirements(self, requirements: Dict[str, str]) -> bool:
        """Install all packages from the requirements dictionary."""
        temp_requirements = self.venv_path / 'temp_requirements.txt'
        try:
            # Create temporary requirements file
            with open(temp_requirements, 'w') as f:
                for package, version in requirements.items():
                    if version:
                        f.write(f"{package}=={version}\n")
                    else:
                        f.write(f"{package}\n")

            # Install requirements
            success, output = self.run_pip_command(
                ['install', '-r', str(temp_requirements)]
            )
            if not success:
                print(f"Failed to install requirements: {output}")
            return success
        finally:
            # Clean up temporary file
            if temp_requirements.exists():
                temp_requirements.unlink()

    def get_installed_packages(self) -> Dict[str, str]:
        """Get a dictionary of installed packages and their versions."""
        success, output = self.run_pip_command(['list', '--format=json'])
        if not success:
            return {}
        
        import json
        try:
            packages = json.loads(output)
            return {pkg['name']: pkg['version'] for pkg in packages}
        except json.JSONDecodeError:
            return {}

    def verify_installation(self, requirements: Dict[str, str]) -> bool:
        """Verify that all required packages are installed with correct versions."""
        installed = self.get_installed_packages()
        for package, version in requirements.items():
            if package.lower() not in {k.lower() for k in installed.keys()}:
                print(f"Package {package} is not installed")
                return False
            if version and installed[package] != version:
                print(f"Package {package} version mismatch: "
                      f"expected {version}, got {installed[package]}")
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
                cwd=self.project_path
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)

    def cleanup(self):
        """Clean up the virtual environment."""
        try:
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
        except Exception as e:
            print(f"Error cleaning up virtual environment: {str(e)}") 