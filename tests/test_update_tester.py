"""
Tests for the update tester module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from package_updater.update_tester import UpdateTester, UpdateResult, PackageUpdateStatus

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with test files."""
    # Create a requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("""
requests==2.25.1
pytest==6.2.4
    """.strip())

    # Create a test file
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_sample.py"
    test_file.write_text("""
def test_simple():
    assert True
    """.strip())

    return tmp_path

@pytest.fixture
def update_tester(temp_project_dir):
    """Create an UpdateTester instance."""
    tester = UpdateTester(str(temp_project_dir))
    yield tester
    tester.cleanup()

def test_setup_test_environment(update_tester):
    """Test setting up the test environment."""
    assert update_tester.setup_test_environment()
    assert update_tester.env_manager.venv_path.exists()

def test_run_tests(update_tester):
    """Test running tests."""
    update_tester.setup_test_environment()
    success, output = update_tester.run_tests()
    assert success
    assert "test_simple" in output

@patch('package_updater.package_manager.PackageManager.get_latest_version')
@patch('package_updater.package_manager.PackageManager.get_version_range')
def test_find_compatible_update(mock_get_range, mock_get_latest, update_tester):
    """Test finding compatible updates for a package."""
    # Mock version information
    mock_get_latest.return_value = "2.26.0"
    mock_get_range.return_value = ["2.25.1", "2.25.2", "2.26.0"]

    # Test update process
    result = update_tester.find_compatible_update("requests")
    
    assert isinstance(result, PackageUpdateStatus)
    assert result.package_name == "requests"
    assert result.current_version == "2.25.1"
    assert result.target_version == "2.26.0"
    assert len(result.tested_versions) > 0

def test_test_package_update(update_tester):
    """Test updating a single package."""
    update_tester.setup_test_environment()
    
    # Test with a known good version
    result = update_tester.test_package_update("pytest", "6.2.5")
    assert isinstance(result, UpdateResult)
    assert result.old_version == "6.2.4"
    assert result.new_version == "6.2.5"

def test_update_all_packages(update_tester):
    """Test updating all packages."""
    results = update_tester.update_all_packages()
    
    assert isinstance(results, dict)
    assert "requests" in results
    assert "pytest" in results
    
    for package_status in results.values():
        assert isinstance(package_status, PackageUpdateStatus)
        assert package_status.current_version
        assert package_status.target_version

def test_cleanup(temp_project_dir):
    """Test cleanup process."""
    tester = UpdateTester(str(temp_project_dir))
    tester.setup_test_environment()
    
    venv_path = tester.env_manager.venv_path
    assert venv_path.exists()
    
    tester.cleanup()
    assert not venv_path.exists()

def test_logging(update_tester):
    """Test that logging is working."""
    assert update_tester.log_file.exists()
    assert update_tester.log_dir.exists()
    
    # Perform some operations that should generate logs
    update_tester.setup_test_environment()
    update_tester.run_tests()
    
    # Check that log file has content
    log_content = update_tester.log_file.read_text()
    assert "Setting up test environment" in log_content
    assert "Running tests" in log_content 