"""
Module for updating package requirement files with new versions.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FileUpdater:
    """Class for updating package requirement files with new versions."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.requirements_file = self.project_path / "requirements.txt"
        self.pipfile = self.project_path / "Pipfile"
        self.backup_dir = self.project_path / "requirement_backups"
        self.backup_dir.mkdir(exist_ok=True)

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of the original file."""
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.{timestamp}.bak"

        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error creating backup: %s", str(e))
            return None

    def _restore_from_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore a file from its backup."""
        try:
            shutil.copy2(backup_path, target_path)
            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error restoring from backup: %s", str(e))
            return False

    def update_requirements_txt(self, updates: Dict[str, str]) -> bool:
        """Update requirements.txt with new package versions."""
        logger.info("Updating requirements.txt with %s package versions", len(updates))
        if not self.requirements_file.exists():
            return False

        # Create backup
        backup_path = self._create_backup(self.requirements_file)
        if not backup_path:
            return False

        try:
            # Read current requirements
            with open(self.requirements_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Update versions
            new_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    new_lines.append(line)
                    continue

                # Parse package name and version specifier
                match = re.match(r"^([^=<>]+)(.*)", line)
                if not match:
                    new_lines.append(line)
                    continue

                package_name = match.group(1).strip()
                if package_name in updates:
                    new_lines.append(f"{package_name}=={updates[package_name]}")
                else:
                    new_lines.append(line)

            # Write updated requirements
            with open(self.requirements_file, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error updating requirements.txt: %s", str(e))
            if backup_path:
                self._restore_from_backup(backup_path, self.requirements_file)
            return False

    def update_pipfile(self, updates: Dict[str, str]) -> bool:
        """Update Pipfile with new package versions."""
        logger.info("Updating Pipfile with %s package versions", len(updates))
        if not self.pipfile.exists():
            return False

        # Create backup
        backup_path = self._create_backup(self.pipfile)
        if not backup_path:
            return False

        try:
            # Read current Pipfile
            with open(self.pipfile, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Update versions
            new_lines = []
            in_packages_section = False
            for line in lines:
                if line.strip() == "[packages]":
                    in_packages_section = True
                    new_lines.append(line)
                    continue
                if line.strip().startswith("["):
                    in_packages_section = False
                    new_lines.append(line)
                    continue

                if in_packages_section:
                    # Parse package name and version
                    match = re.match(r'^([^=<>]+)\s*=\s*"([^"]+)"', line.strip())
                    if match:
                        package_name = match.group(1).strip()
                        if package_name in updates:
                            new_lines.append(
                                f'{package_name} = "{updates[package_name]}"\n'
                            )
                            continue

                new_lines.append(line)

            # Write updated Pipfile
            with open(self.pipfile, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error updating Pipfile: %s", str(e))
            if backup_path:
                self._restore_from_backup(backup_path, self.pipfile)
            return False

    def update_package_files(self, updates: Dict[str, str]) -> Dict[str, bool]:
        """Update all package files with new versions."""
        logger.info("Updating package files")
        results = {}

        if self.requirements_file.exists():
            results["requirements.txt"] = self.update_requirements_txt(updates)

        if self.pipfile.exists():
            results["Pipfile"] = self.update_pipfile(updates)

        return results

    # def get_latest_backup(self, file_name: str) -> Optional[Path]:
    #     """Get the most recent backup for a given file."""
    #     logger.info("Getting latest backup for %s", file_name)
    #     backups = list(self.backup_dir.glob(f"{file_name}.*"))
    #     return max(backups, key=lambda p: p.stat().st_mtime) if backups else None
