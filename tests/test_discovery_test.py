"""
Tests for the test discovery module.
"""

import os
import pytest
from package_updater.test_discovery import TestDiscovery

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with test files."""
    # Create a valid test file
    test_file1 = tmp_path / "test_valid.py"
    test_file1.write_text("""
def test_something():
    assert True

def test_another():
    assert 1 + 1 == 2
""")

    # Create a non-test Python file
    regular_file = tmp_path / "regular.py"
    regular_file.write_text("print('not a test')")

    # Create an invalid test file
    test_file2 = tmp_path / "test_invalid.py"
    test_file2.write_text("this is not valid python")

    return tmp_path

def test_find_test_files(temp_project_dir):
    """Test that test files are correctly identified."""
    discoverer = TestDiscovery(str(temp_project_dir))
    test_files = discoverer.find_test_files()
    
    assert len(test_files) == 2
    assert any('test_valid.py' in f for f in test_files)
    assert any('test_invalid.py' in f for f in test_files)
    assert not any('regular.py' in f for f in test_files)

def test_validate_test_file(temp_project_dir):
    """Test that test file validation works correctly."""
    discoverer = TestDiscovery(str(temp_project_dir))
    
    valid_file = os.path.join(str(temp_project_dir), "test_valid.py")
    invalid_file = os.path.join(str(temp_project_dir), "test_invalid.py")
    
    assert discoverer.validate_test_file(valid_file)
    assert not discoverer.validate_test_file(invalid_file)

def test_extract_test_functions(temp_project_dir):
    """Test that test functions are correctly extracted."""
    discoverer = TestDiscovery(str(temp_project_dir))
    valid_file = os.path.join(str(temp_project_dir), "test_valid.py")
    
    test_functions = discoverer.extract_test_functions(valid_file)
    assert len(test_functions) == 2
    assert "test_something" in test_functions
    assert "test_another" in test_functions

def test_discover_and_validate_tests(temp_project_dir):
    """Test the complete test discovery and validation process."""
    discoverer = TestDiscovery(str(temp_project_dir))
    results = discoverer.discover_and_validate_tests()
    
    assert len(results) == 2
    
    valid_file = os.path.join(str(temp_project_dir), "test_valid.py")
    assert results[valid_file]['valid']
    assert len(results[valid_file]['test_functions']) == 2
    
    invalid_file = os.path.join(str(temp_project_dir), "test_invalid.py")
    assert not results[invalid_file]['valid']
    assert len(results[invalid_file]['test_functions']) == 0 