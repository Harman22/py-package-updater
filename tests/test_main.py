"""
Tests for the command-line interface.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from package_updater.__main__ import (analyze_updates, apply_updates,
                                      filter_updates, main,
                                      validate_project_path, validate_tests)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with sample files."""
    # Create requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        """
requests==2.25.1
pytest==6.2.4
    """.strip()
    )

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
    all_updates = {"requests": "2.26.0", "pytest": "6.2.5", "flask": "2.0.1"}

    # Test with specific packages
    selected = filter_updates(all_updates, ["requests", "pytest"])
    assert "requests" in selected
    assert "pytest" in selected
    assert "flask" not in selected

    # Test with no filter
    assert filter_updates(all_updates, None) == all_updates


@patch("package_updater.__main__.TestDiscovery")
def test_validate_tests_valid(mock_test_discovery, temp_project_dir):
    """Test validate_tests with valid test files."""
    mock_test_discovery.return_value.find_test_files.return_value = ["test_sample.py"]
    mock_test_discovery.return_value.discover_and_validate_tests.return_value = {
        "test_sample.py": {
            "valid": True,
            "test_functions": ["test_simple"],
            "relative_path": "./",
        }
    }
    assert validate_tests(str(temp_project_dir)) is True


@patch("package_updater.__main__.TestDiscovery")
def test_validate_tests_invalid(mock_test_discovery, temp_project_dir):
    """Test validate_tests with no valid test files."""
    mock_test_discovery.return_value.find_test_files.return_value = []
    assert validate_tests(str(temp_project_dir)) is False


@patch("package_updater.__main__.UpdateTester")
def test_analyze_updates_with_tests(mock_update_tester, temp_project_dir):
    """Test analyze_updates when tests are not skipped."""
    mock_update_tester.return_value.update_all_packages.return_value = {
        "requests": Mock(compatible_version="2.26.0", current_version="2.25.1"),
        "pytest": Mock(compatible_version="6.2.5", current_version="6.2.4"),
    }
    args = Mock(skip_tests=False, packages=None)
    updates = analyze_updates(temp_project_dir, args)
    assert updates == {"requests": "2.26.0", "pytest": "6.2.5"}


@patch("package_updater.__main__.PackageManager")
def test_analyze_updates_skip_tests(mock_package_manager):
    """Test analyze_updates when tests are skipped."""
    # Mock the PackageManager's behavior
    mock_package_manager.return_value.current_packages = {
        "requests": {"current_version": "1.0.0"},
        "pytest": {"current_version": "2.0.0"},
    }
    mock_package_manager.return_value.get_latest_version.side_effect = lambda pkg: Mock(
        compatible_version={"requests": "1.1.0", "pytest": "2.1.0"}[pkg],
        current_version={"requests": "1.0.0", "pytest": "2.0.0"}[pkg],
    )

    # Mock arguments
    args = Mock(skip_tests=True, packages=None)

    # Temporary project path
    temp_project_dir = Path("/tmp/test_project")

    # Call the function
    updates = analyze_updates(temp_project_dir, args)

    # Assert the updates are as expected
    assert updates == {
        "requests": "1.1.0",
        "pytest": "2.1.0",
    }


@patch("package_updater.__main__.FileUpdater")
def test_apply_updates_dry_run(mock_file_updater, temp_project_dir):
    """Test apply_updates in dry-run mode."""
    updates = {"requests": "2.26.0", "pytest": "6.2.5"}
    args = Mock(dry_run=True)
    apply_updates(temp_project_dir, updates, args)
    mock_file_updater.return_value.update_package_files.assert_not_called()


@patch("package_updater.__main__.FileUpdater")
def test_apply_updates_real_run(mock_file_updater, temp_project_dir):
    """Test apply_updates in real mode."""
    updates = {"requests": "2.26.0", "pytest": "6.2.5"}
    args = Mock(dry_run=False)
    mock_file_updater.return_value.update_package_files.return_value = {
        "requirements.txt": True
    }
    apply_updates(temp_project_dir, updates, args)
    mock_file_updater.return_value.update_package_files.assert_called_once_with(updates)


def test_main_invalid_path():
    """Test main function with invalid project path."""
    result = main(["/nonexistent/path"])
    assert result == 1


@patch("logging.basicConfig")
def test_setup_logging_verbose(mock_basic_config):
    """Test setup_logging with verbose mode."""
    from package_updater.__main__ import setup_logging

    setup_logging(verbose=True)
    mock_basic_config.assert_called_once_with(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


@patch("logging.basicConfig")
def test_setup_logging_non_verbose(mock_basic_config):
    """Test setup_logging without verbose mode."""
    from package_updater.__main__ import setup_logging

    setup_logging(verbose=False)
    mock_basic_config.assert_called_once_with(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def test_create_parser():
    """Test create_parser for correct argument parsing."""
    from package_updater.__main__ import create_parser

    parser = create_parser()
    args = parser.parse_args([".", "--packages", "requests", "--dry-run", "--verbose"])
    assert args.project_path == "."
    assert args.packages == ["requests"]
    assert args.dry_run is True
    assert args.verbose is True


@patch("package_updater.__main__.validate_project_path")
@patch("package_updater.__main__.analyze_updates")
@patch("package_updater.__main__.apply_updates")
def test_main_successful_run(
    mock_apply_updates,
    mock_analyze_updates,
    mock_validate_project_path,
    temp_project_dir,
):
    """Test main function with a successful run."""
    mock_validate_project_path.return_value = temp_project_dir
    mock_analyze_updates.return_value = {"requests": "2.26.0"}
    mock_apply_updates.return_value = None

    result = main([str(temp_project_dir)])
    assert result == 0
    mock_validate_project_path.assert_called_once_with(str(temp_project_dir))
    mock_analyze_updates.assert_called_once()
    mock_apply_updates.assert_called_once()


@patch("package_updater.__main__.validate_project_path")
def test_main_keyboard_interrupt(mock_validate_project_path, temp_project_dir):
    """Test main function handling KeyboardInterrupt."""
    mock_validate_project_path.side_effect = KeyboardInterrupt
    result = main([str(temp_project_dir)])
    assert result == 130


@patch("package_updater.__main__.validate_project_path")
def test_main_exception_handling(mock_validate_project_path, temp_project_dir):
    """Test main function handling generic exceptions."""
    mock_validate_project_path.side_effect = Exception("Test exception")
    result = main([str(temp_project_dir)])
    assert result == 1
