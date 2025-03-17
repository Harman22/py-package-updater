"""
Tests for the command-line interface.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from package_updater.__main__ import main, validate_project_path, filter_updates

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with sample files."""
    # Create requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("""
requests==2.25.1
pytest==6.2.4
    """.strip())

    # Create test directory
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_sample.py"
    test_file.write_text("def test_simple(): assert True")

    return tmp_path

def test_validate_project_path_valid(temp_project_dir):
    """Test project path validation with valid path."""
    result = validate_project_path(str(temp_project_dir))
    assert result == temp_project_dir

def test_validate_project_path_invalid():
    """Test project path validation with invalid path."""
    assert validate_project_path("/nonexistent/path") is None

def test_validate_project_path_no_requirements(tmp_path):
    """Test project path validation with no requirements files."""
    assert validate_project_path(str(tmp_path)) is None

def test_filter_updates():
    """Test filtering updates by package name."""
    all_updates = {
        "requests": "2.26.0",
        "pytest": "6.2.5",
        "flask": "2.0.1"
    }
    
    # Test with specific packages
    selected = filter_updates(all_updates, ["requests", "pytest"])
    assert "requests" in selected
    assert "pytest" in selected
    assert "flask" not in selected
    
    # Test with no filter
    assert filter_updates(all_updates, None) == all_updates

@patch('package_updater.update_tester.UpdateTester')
@patch('package_updater.report_generator.ReportGenerator')
@patch('package_updater.file_updater.FileUpdater')
def test_main_successful_run(
    mock_file_updater,
    mock_report_generator,
    mock_update_tester,
    temp_project_dir
):
    """Test successful execution of main function."""
    # Mock update testing results
    mock_update_tester.return_value.update_all_packages.return_value = {
        "requests": Mock(
            compatible_version="2.26.0",
            current_version="2.25.1"
        ),
        "pytest": Mock(
            compatible_version="6.2.5",
            current_version="6.2.4"
        )
    }
    
    # Mock report generation
    mock_report_generator.return_value.generate_and_save_report.return_value = \
        temp_project_dir / "report.md"
    
    # Mock file updates
    mock_file_updater.return_value.update_package_files.return_value = {
        "requirements.txt": True
    }
    
    # Run main function
    result = main([str(temp_project_dir)])
    assert result == 0

def test_main_dry_run(temp_project_dir):
    """Test dry run mode."""
    result = main([str(temp_project_dir), "--dry-run"])
    assert result == 0
    
    # Verify requirements.txt wasn't modified
    content = (temp_project_dir / "requirements.txt").read_text()
    assert "requests==2.25.1" in content
    assert "pytest==6.2.4" in content

def test_main_specific_packages(temp_project_dir):
    """Test updating specific packages."""
    result = main([
        str(temp_project_dir),
        "--packages", "requests",
        "--dry-run"
    ])
    assert result == 0

def test_main_invalid_path():
    """Test main function with invalid project path."""
    result = main(["/nonexistent/path"])
    assert result == 1

@patch('package_updater.update_tester.UpdateTester')
def test_main_error_handling(mock_update_tester, temp_project_dir):
    """Test error handling in main function."""
    mock_update_tester.return_value.update_all_packages.side_effect = \
        Exception("Test error")
    
    result = main([str(temp_project_dir)])
    assert result == 1

def test_main_keyboard_interrupt(temp_project_dir):
    """Test handling of keyboard interrupt."""
    with patch('package_updater.update_tester.UpdateTester') as mock:
        mock.return_value.update_all_packages.side_effect = KeyboardInterrupt()
        result = main([str(temp_project_dir)])
        assert result == 130 