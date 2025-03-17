"""
Tests for the environment manager module.
"""

import os
import sys
import pytest
from pathlib import Path
from package_updater.environment_manager import EnvironmentManager

@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path

@pytest.fixture
def env_manager(temp_project_dir):
    """Create an environment manager instance."""
    manager = EnvironmentManager(str(temp_project_dir))
    manager.create_virtual_environment()
    yield manager
    manager.cleanup()

def test_create_virtual_environment(temp_project_dir):
    """Test virtual environment creation."""
    manager = EnvironmentManager(str(temp_project_dir))
    assert manager.create_virtual_environment()
    
    venv_path = Path(temp_project_dir) / '.venv'
    assert venv_path.exists()
    
    # Check for key virtual environment files
    python_exec = 'python.exe' if sys.platform == 'win32' else 'python'
    pip_exec = 'pip.exe' if sys.platform == 'win32' else 'pip'
    
    bin_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
    assert (venv_path / bin_dir / python_exec).exists()
    assert (venv_path / bin_dir / pip_exec).exists()

def test_install_single_package(env_manager):
    """Test installing a single package."""
    # Install a small, reliable package
    assert env_manager.install_package('six')
    installed = env_manager.get_installed_packages()
    assert 'six' in installed

def test_install_specific_version(env_manager):
    """Test installing a specific package version."""
    assert env_manager.install_package('requests', '2.25.1')
    installed = env_manager.get_installed_packages()
    assert 'requests' in installed
    assert installed['requests'] == '2.25.1'

def test_install_requirements(env_manager):
    """Test installing multiple packages from requirements."""
    requirements = {
        'six': '1.16.0',
        'pytest': '7.0.0'
    }
    assert env_manager.install_requirements(requirements)
    assert env_manager.verify_installation(requirements)

def test_get_installed_packages(env_manager):
    """Test getting list of installed packages."""
    # Install some packages first
    requirements = {
        'six': '1.16.0',
        'pytest': '7.0.0'
    }
    env_manager.install_requirements(requirements)
    
    installed = env_manager.get_installed_packages()
    assert 'six' in installed
    assert 'pytest' in installed
    assert installed['six'] == '1.16.0'
    assert installed['pytest'] == '7.0.0'

def test_verify_installation(env_manager):
    """Test verification of installed packages."""
    requirements = {
        'six': '1.16.0',
        'pytest': '7.0.0'
    }
    env_manager.install_requirements(requirements)
    
    # Test correct verification
    assert env_manager.verify_installation(requirements)
    
    # Test incorrect version verification
    wrong_requirements = {
        'six': '1.15.0',  # Different version
        'pytest': '7.0.0'
    }
    assert not env_manager.verify_installation(wrong_requirements)
    
    # Test missing package verification
    missing_package = {
        'nonexistent-package': '1.0.0'
    }
    assert not env_manager.verify_installation(missing_package)

def test_run_python_command(env_manager):
    """Test running Python commands in the virtual environment."""
    success, output = env_manager.run_python_command(['-c', 'print("test")'])
    assert success
    assert output.strip() == 'test'

def test_cleanup(temp_project_dir):
    """Test cleanup of virtual environment."""
    manager = EnvironmentManager(str(temp_project_dir))
    manager.create_virtual_environment()
    
    venv_path = Path(temp_project_dir) / '.venv'
    assert venv_path.exists()
    
    manager.cleanup()
    assert not venv_path.exists() 