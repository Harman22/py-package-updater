"""
Tests for the file updater module.
"""

import pytest
from pathlib import Path
from package_updater.file_updater import FileUpdater

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with sample files."""
    # Create requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("""
# Sample requirements file
requests>=2.25.1
pytest==6.2.4
flask==2.0.0
# Comment line
urllib3<2.0.0
    """.strip())

    # Create Pipfile
    pipfile = tmp_path / "Pipfile"
    pipfile.write_text("""
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = ">=2.25.1"
pytest = "==6.2.4"
flask = "==2.0.0"

[dev-packages]
black = "*"
    """.strip())

    return tmp_path

@pytest.fixture
def file_updater(temp_project_dir):
    """Create a FileUpdater instance."""
    return FileUpdater(str(temp_project_dir))

@pytest.fixture
def sample_updates():
    """Create sample package updates."""
    return {
        "requests": "2.25.2",
        "pytest": "6.2.5",
        "flask": "2.0.1"
    }

def test_backup_creation(file_updater):
    """Test backup file creation."""
    backup = file_updater._create_backup(file_updater.requirements_file)
    assert backup is not None
    assert backup.exists()
    assert backup.parent == file_updater.backup_dir

def test_restore_from_backup(file_updater):
    """Test restoring from backup."""
    # Create a backup
    backup = file_updater._create_backup(file_updater.requirements_file)
    
    # Modify original file
    file_updater.requirements_file.write_text("modified content")
    
    # Restore from backup
    assert file_updater._restore_from_backup(backup, file_updater.requirements_file)
    assert "requests>=2.25.1" in file_updater.requirements_file.read_text()

def test_update_requirements_txt(file_updater, sample_updates):
    """Test updating requirements.txt."""
    assert file_updater.update_requirements_txt(sample_updates)
    
    content = file_updater.requirements_file.read_text()
    assert "requests==2.25.2" in content
    assert "pytest==6.2.5" in content
    assert "flask==2.0.1" in content
    assert "urllib3<2.0.0" in content  # Unchanged line
    assert "# Comment line" in content  # Preserved comment

def test_update_pipfile(file_updater, sample_updates):
    """Test updating Pipfile."""
    assert file_updater.update_pipfile(sample_updates)
    
    content = file_updater.pipfile.read_text()
    assert 'requests = "2.25.2"' in content
    assert 'pytest = "6.2.5"' in content
    assert 'flask = "2.0.1"' in content
    assert '[dev-packages]' in content  # Preserved section
    assert 'black = "*"' in content  # Unchanged dev package

def test_update_package_files(file_updater, sample_updates):
    """Test updating all package files."""
    results = file_updater.update_package_files(sample_updates)
    
    assert results['requirements.txt']
    assert results['Pipfile']
    assert len(results) == 2

def test_get_latest_backup(file_updater, sample_updates):
    """Test getting the latest backup file."""
    # Create multiple backups
    file_updater.update_requirements_txt(sample_updates)
    file_updater.update_requirements_txt({"pytest": "6.2.6"})
    
    latest_backup = file_updater.get_latest_backup("requirements.txt")
    assert latest_backup is not None
    assert latest_backup.exists()
    assert latest_backup == max(
        file_updater.backup_dir.glob("requirements.txt.*"),
        key=lambda p: p.stat().st_mtime
    )

def test_backup_on_error(file_updater, sample_updates, monkeypatch):
    """Test that backup is restored on error."""
    # Make writing fail after backup is created
    def mock_write(*args, **kwargs):
        raise Exception("Write error")
    
    original_content = file_updater.requirements_file.read_text()
    
    # Patch the built-in open function for writing
    monkeypatch.setattr('builtins.open', mock_write)
    
    # Attempt update (should fail)
    assert not file_updater.update_requirements_txt(sample_updates)
    
    # Check content is restored
    assert file_updater.requirements_file.read_text() == original_content 