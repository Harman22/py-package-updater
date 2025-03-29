import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from package_updater.package_manager import PackageManager

project_path = "/fake/project/path"
package_manager = PackageManager(project_path)


@patch("os.path.exists")
def test_detect_package_file_requirements(mock_exists):
    mock_exists.side_effect = lambda path: path == os.path.join(project_path, "requirements.txt")
    result = package_manager.detect_package_file()
    assert result == os.path.join(project_path, "requirements.txt")


@patch("os.path.exists")
def test_detect_package_file_pipfile(mock_exists):
    mock_exists.side_effect = lambda path: path == os.path.join(project_path, "Pipfile")
    result = package_manager.detect_package_file()
    assert result == os.path.join(project_path, "Pipfile")


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="package1==1.0.0\npackage2>=2.0.0\n",
)
def test_parse_requirements_txt(mock_file):
    result = package_manager.parse_requirements_txt()
    assert result == {"package1": "1.0.0", "package2": "2.0.0"}


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data='[packages]\n"package1" = "==1.0.0"\n"package2" = ">=2.0.0"\n',
)
def test_parse_pipfile(mock_file):
    result = package_manager.parse_pipfile()
    assert result == {"package1": "1.0.0", "package2": "2.0.0"}


@patch("requests.get")
def test_get_latest_version(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": "3.0.0"}}
    mock_get.return_value = mock_response

    result = package_manager.get_latest_version("package1")
    assert result == "3.0.0"


@patch("requests.get")
def test_get_version_range(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"releases": {"1.0.0": {}, "2.0.0": {}, "3.0.0": {}}}
    mock_get.return_value = mock_response

    result = package_manager.get_version_range("package1", "1.0.0", "3.0.0")
    assert result == ["1.0.0", "2.0.0", "3.0.0"]


@patch("package_updater.package_manager.PackageManager.get_latest_version")
@patch("package_updater.package_manager.PackageManager.get_version_range")
@patch("package_updater.package_manager.PackageManager.parse_requirements_txt")
@patch("package_updater.package_manager.PackageManager.detect_package_file")
def test_analyze_packages(mock_detect, mock_parse, mock_range, mock_latest):
    mock_detect.return_value = os.path.join(project_path, "requirements.txt")
    mock_parse.return_value = {"package1": "1.0.0"}
    mock_latest.return_value = "3.0.0"
    mock_range.return_value = ["1.0.0", "2.0.0", "3.0.0"]

    result = package_manager.analyze_packages()
    assert result == {
        "package1": {
            "current_version": "1.0.0",
            "latest_version": "3.0.0",
            "available_versions": ["1.0.0", "2.0.0", "3.0.0"],
            "needs_update": True,
        }
    }
