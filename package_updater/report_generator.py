"""
Module for generating update testing reports.
"""

import os
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from .update_tester import PackageUpdateStatus

class ReportGenerator:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.reports_dir = self.project_path / 'update_reports'
        self.reports_dir.mkdir(exist_ok=True)

    def _generate_package_summary(self, status: PackageUpdateStatus) -> List[str]:
        """Generate markdown summary for a single package."""
        lines = []
        
        # Package header
        lines.append(f"### {status.package_name}")
        lines.append("")
        
        # Version information
        lines.append("**Version Information:**")
        lines.append(f"- Current Version: `{status.current_version}`")
        lines.append(f"- Latest Version: `{status.target_version}`")
        if status.compatible_version:
            lines.append(f"- Highest Compatible Version: `{status.compatible_version}`")
        else:
            lines.append("- No compatible update found")
        lines.append("")
        
        # Testing summary
        lines.append("**Testing Summary:**")
        lines.append(f"- Versions Tested: {len(status.tested_versions)}")
        lines.append(f"- Failed Versions: {len(status.failed_versions)}")
        lines.append("")
        
        # Failed versions details
        if status.failed_versions:
            lines.append("**Failed Versions:**")
            for version, error in status.failed_versions.items():
                lines.append(f"- `{version}`: {error}")
            lines.append("")
        
        # Update recommendation
        lines.append("**Recommendation:**")
        if status.compatible_version and status.compatible_version != status.current_version:
            lines.append(f"✅ Update to version `{status.compatible_version}`")
        elif status.compatible_version == status.current_version:
            lines.append("✅ Package is already at the highest compatible version")
        else:
            lines.append("❌ Keep current version - no compatible update found")
        lines.append("")
        
        return lines

    def generate_report(self, results: Dict[str, PackageUpdateStatus]) -> str:
        """Generate a complete markdown report from update results."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines = [
            "# Package Update Test Report",
            "",
            f"Generated on: {timestamp}",
            "",
            "## Summary",
            ""
        ]

        # Overall statistics
        total_packages = len(results)
        updatable_packages = sum(
            1 for status in results.values()
            if status.compatible_version and status.compatible_version != status.current_version
        )
        failed_packages = sum(
            1 for status in results.values()
            if not status.compatible_version or len(status.failed_versions) > 0
        )

        report_lines.extend([
            f"- Total Packages Analyzed: {total_packages}",
            f"- Packages with Available Updates: {updatable_packages}",
            f"- Packages with Failed Updates: {failed_packages}",
            "",
            "## Quick Update Guide",
            ""
        ])

        # Quick update guide
        for status in results.values():
            if status.compatible_version and status.compatible_version != status.current_version:
                report_lines.append(
                    f"- `{status.package_name}`: "
                    f"`{status.current_version}` → `{status.compatible_version}`"
                )
        report_lines.append("")

        # Detailed results
        report_lines.append("## Detailed Results")
        report_lines.append("")
        
        # Sort packages by name for consistent ordering
        for package_name in sorted(results.keys()):
            report_lines.extend(self._generate_package_summary(results[package_name]))

        return "\n".join(report_lines)

    def save_report(self, report_content: str) -> Path:
        """Save the report to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"update_report_{timestamp}.md"
        
        report_file.write_text(report_content)
        return report_file

    def generate_and_save_report(self, results: Dict[str, PackageUpdateStatus]) -> Path:
        """Generate and save a report in one step."""
        report_content = self.generate_report(results)
        return self.save_report(report_content) 