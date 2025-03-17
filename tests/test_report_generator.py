"""
Tests for the report generator module.
"""

import pytest
from pathlib import Path
from package_updater.report_generator import ReportGenerator
from package_updater.update_tester import PackageUpdateStatus

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path

@pytest.fixture
def report_generator(temp_project_dir):
    """Create a ReportGenerator instance."""
    return ReportGenerator(str(temp_project_dir))

@pytest.fixture
def sample_results():
    """Create sample update results for testing."""
    return {
        "requests": PackageUpdateStatus(
            package_name="requests",
            current_version="2.25.1",
            target_version="2.26.0",
            compatible_version="2.25.2",
            tested_versions=["2.25.2", "2.26.0"],
            failed_versions={"2.26.0": "Tests failed"}
        ),
        "pytest": PackageUpdateStatus(
            package_name="pytest",
            current_version="6.2.4",
            target_version="6.2.5",
            compatible_version="6.2.5",
            tested_versions=["6.2.5"],
            failed_versions={}
        ),
        "flask": PackageUpdateStatus(
            package_name="flask",
            current_version="2.0.0",
            target_version="2.1.0",
            compatible_version=None,
            tested_versions=["2.0.1", "2.1.0"],
            failed_versions={
                "2.0.1": "Installation failed",
                "2.1.0": "Tests failed"
            }
        )
    }

def test_report_directory_creation(report_generator):
    """Test that the reports directory is created."""
    assert report_generator.reports_dir.exists()
    assert report_generator.reports_dir.is_dir()

def test_generate_package_summary(report_generator, sample_results):
    """Test generating summary for a single package."""
    status = sample_results["requests"]
    summary = report_generator._generate_package_summary(status)
    
    summary_text = "\n".join(summary)
    assert "requests" in summary_text
    assert "2.25.1" in summary_text
    assert "2.26.0" in summary_text
    assert "2.25.2" in summary_text
    assert "Tests failed" in summary_text

def test_generate_report(report_generator, sample_results):
    """Test generating a complete report."""
    report = report_generator.generate_report(sample_results)
    
    # Check header
    assert "# Package Update Test Report" in report
    
    # Check summary statistics
    assert "Total Packages Analyzed: 3" in report
    assert "Packages with Available Updates: 1" in report
    assert "Packages with Failed Updates: 1" in report
    
    # Check package details
    assert "### requests" in report
    assert "### pytest" in report
    assert "### flask" in report
    
    # Check recommendations
    assert "Update to version" in report
    assert "Keep current version" in report

def test_save_report(report_generator):
    """Test saving a report to file."""
    content = "# Test Report\nThis is a test."
    report_file = report_generator.save_report(content)
    
    assert report_file.exists()
    assert report_file.is_file()
    assert report_file.read_text() == content

def test_generate_and_save_report(report_generator, sample_results):
    """Test generating and saving a report in one step."""
    report_file = report_generator.generate_and_save_report(sample_results)
    
    assert report_file.exists()
    assert report_file.is_file()
    
    content = report_file.read_text()
    assert "# Package Update Test Report" in content
    assert "### requests" in content
    assert "### pytest" in content
    assert "### flask" in content 