"""
Module for detecting and managing package versions.
"""

import os
import re
from typing import Dict, List, Optional
import requests
from packaging import version

class PackageManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.requirements_file = os.path.join(project_path, "requirements.txt")
        self.pipfile = os.path.join(project_path, "Pipfile")
        self.current_packages: Dict[str, str] = {}
        self.latest_versions: Dict[str, str] = {}

    def detect_package_file(self) -> Optional[str]:
        """Detect whether the project uses requirements.txt or Pipfile."""
        if os.path.exists(self.requirements_file):
            return self.requirements_file
        elif os.path.exists(self.pipfile):
            return self.pipfile
        return None

    def parse_requirements_txt(self) -> Dict[str, str]:
        """Parse requirements.txt file and extract package versions."""
        packages = {}
        with open(self.requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle different requirement formats
                    if '>=' in line:
                        name, ver = line.split('>=')
                    elif '==' in line:
                        name, ver = line.split('==')
                    else:
                        name = line.split()[0]
                        ver = None
                    name = re.sub(r'[^a-zA-Z0-9-_.]', '', name)
                    packages[name.strip()] = ver.strip() if ver else None
        return packages

    def parse_pipfile(self) -> Dict[str, str]:
        """Parse Pipfile and extract package versions."""
        # TODO: Implement Pipfile parsing
        raise NotImplementedError("Pipfile parsing not yet implemented")

    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Query PyPI API for the latest version of a package."""
        try:
            response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
            if response.status_code == 200:
                return response.json()['info']['version']
            return None
        except requests.RequestException:
            return None

    def get_version_range(self, package_name: str, current_version: str, latest_version: str) -> List[str]:
        """Get list of versions between current and latest."""
        try:
            response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
            if response.status_code != 200:
                return []

            all_versions = list(response.json()['releases'].keys())
            all_versions.sort(key=lambda x: version.parse(x))

            current_idx = next((i for i, v in enumerate(all_versions) 
                              if version.parse(v) >= version.parse(current_version)), 0)
            latest_idx = next((i for i, v in enumerate(all_versions) 
                             if version.parse(v) >= version.parse(latest_version)), len(all_versions))

            return all_versions[current_idx:latest_idx + 1]
        except (requests.RequestException, version.InvalidVersion):
            return []

    def analyze_packages(self) -> Dict[str, Dict]:
        """Analyze all packages and their available updates."""
        package_file = self.detect_package_file()
        if not package_file:
            raise FileNotFoundError("No requirements.txt or Pipfile found")

        if package_file.endswith('requirements.txt'):
            self.current_packages = self.parse_requirements_txt()
        else:
            self.current_packages = self.parse_pipfile()

        results = {}
        for package_name, current_version in self.current_packages.items():
            if not current_version:
                continue

            latest_version = self.get_latest_version(package_name)
            if not latest_version:
                continue

            self.latest_versions[package_name] = latest_version
            available_versions = self.get_version_range(
                package_name, current_version, latest_version
            )

            results[package_name] = {
                'current_version': current_version,
                'latest_version': latest_version,
                'available_versions': available_versions,
                'needs_update': version.parse(latest_version) > version.parse(current_version)
            }

        return results 