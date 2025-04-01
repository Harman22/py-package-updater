"""
Tests for the update tester module.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from py_package_updater.update_tester import PackageUpdateStatus, UpdateResult, UpdateTester


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with test files."""
    # Create a requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        """
requests==2.32.3
pytest==8.3.4
    """.strip()
    )

    # Create a test file
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_sample.py"
    test_file.write_text(
        """
def test_simple():
    assert True
    """.strip()
    )

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


@patch("py_package_updater.package_manager.PackageManager.get_latest_version")
@patch("py_package_updater.package_manager.PackageManager.get_version_range")
def test_find_compatible_update(mock_get_range, mock_get_latest, update_tester):
    """Test finding compatible updates for a package."""
    # Mock version information
    mock_get_latest.return_value = "2.32.4"
    mock_get_range.return_value = ["2.25.1", "2.25.2", "2.32.4"]

    # Test update process
    result = update_tester.find_compatible_update("requests")

    assert isinstance(result, PackageUpdateStatus)
    assert result.package_name == "requests"
    assert result.current_version == "2.32.3"
    assert result.target_version == "2.32.4"
    assert len(result.tested_versions) > 0


def test_test_package_update(update_tester):
    """Test updating a single package."""
    update_tester.setup_test_environment()

    # Test with a known good version
    result = update_tester.test_package_update("pytest", "6.2.5")
    assert isinstance(result, UpdateResult)


def test_update_all_packages(update_tester):
    """Test updating all packages."""
    update_tester.setup_test_environment()
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


def test_setup_test_environment_failure(update_tester):
    """Test failure in setting up the test environment."""
    with patch.object(update_tester.env_manager, "create_virtual_environment", return_value=False):
        update_tester.setup_test_environment()
        assert not update_tester.setup_test_environment()


def test_test_package_update_failure(update_tester):
    """Test failure in updating a package."""
    update_tester.setup_test_environment()
    with patch.object(update_tester.env_manager, "install_package", return_value=False):

        result = update_tester.test_package_update("pytest", "6.2.5")
        assert not result.success
        assert result.error_message == "Failed to install pytest==6.2.5"


@patch(
    "py_package_updater.package_manager.PackageManager.get_latest_version",
    return_value=None,
)
def test_find_compatible_update_no_latest_version(mock_get_latest, update_tester):
    """Test finding compatible updates when no latest version is available."""
    result = update_tester.find_compatible_update("requests")
    assert result.target_version == "unknown"
    assert result.compatible_version is None


@patch(
    "py_package_updater.package_manager.PackageManager.get_version_range",
    return_value=[],
)
def test_find_compatible_update_no_versions(mock_get_range, update_tester):
    """Test finding compatible updates when no versions are available."""
    result = update_tester.find_compatible_update("requests")
    assert result.tested_versions == []
    assert result.compatible_version is None


def test_run_tests_no_test_files(update_tester):
    """Test running tests when no test files are found."""
    patch.object(update_tester.test_discovery, "find_test_files", return_value=[])
    success, output = update_tester.run_tests()
    assert not success
    assert "No such file or directory" in output
