"""
Module for discovering and validating Python test files in a project.
"""

import ast
import importlib.util
import logging
import os
import subprocess
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class TestDiscovery:
    """Class for discovering and validating Python test files in a project."""

    def __init__(self, project_path: str) -> None:
        self.project_path = project_path
        self.test_files: List[str] = []
        self.test_functions: Dict[str, Set[str]] = {}

    def is_test_file(self, filename: str) -> bool:
        """Check if a file is a test file based on naming convention."""
        return (
            filename.startswith("test_")
            and filename.endswith(".py")
            and not filename.startswith("__")
        )

    def find_test_files(self) -> List[str]:
        """Recursively scan the project directory for test files."""
        logger.debug("Scanning %s for test files", self.project_path)
        self.test_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if self.is_test_file(file):
                    full_path = os.path.join(root, file)
                    self.test_files.append(full_path)
        return self.test_files

    def _has_pytest_decorator(self, node: ast.FunctionDef) -> bool:
        """Check if a function has a pytest decorator."""
        for decorator in node.decorator_list:
            # Handle different decorator formats
            if isinstance(decorator, ast.Name) and decorator.id == "pytest":
                return True
            if isinstance(decorator, ast.Attribute) and isinstance(
                decorator.value, ast.Name
            ):
                if decorator.value.id == "pytest":
                    return True
            if isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Attribute
            ):
                if (
                    isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "pytest"
                ):
                    return True
        return False

    def extract_test_functions(self, file_path: str) -> Set[str]:
        """Extract test function names from a test file using AST."""
        logger.debug("Extracting test functions from %s", file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            test_functions = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue

                # Check for test_ prefix
                if node.name.startswith("test_"):
                    test_functions.add(node.name)
                    continue

                # Check for pytest decorators
                if self._has_pytest_decorator(node):
                    test_functions.add(node.name)

            return test_functions
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error parsing %s: %s", file_path, str(e))
            return set()

    def validate_test_file(self, file_path: str) -> bool:
        """Validate that a test file can be imported and contains valid tests."""
        logger.debug("Validating test file: %s", file_path)
        try:
            # Try to import the module
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Extract and store test functions
            test_functions = self.extract_test_functions(file_path)
            if test_functions:
                self.test_functions[file_path] = test_functions
                return True

            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error validating %s: %s", file_path, str(e))
            return False

    def discover_and_validate_tests(self) -> Dict[str, Dict]:
        """
        Find all test files and validate them.
        Returns a dictionary with test file information.
        """
        logger.info("Discovering and validating test files")
        self.find_test_files()

        results = {}
        for test_file in self.test_files:
            is_valid = self.validate_test_file(test_file)
            results[test_file] = {
                "valid": is_valid,
                "test_functions": list(self.test_functions.get(test_file, set())),
                "relative_path": os.path.relpath(test_file, self.project_path),
            }

        return results

    def run_tests(self, test_files: List[str] = None) -> bool:
        """
        Run pytest on specified test files or all discovered test files.
        Returns True if all tests pass, False otherwise.
        """
        logger.info("Running tests")
        files_to_test = test_files if test_files else self.test_files
        if not files_to_test:
            return False

        try:
            # Run pytest using subprocess
            command = ["pytest"] + files_to_test
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.returncode == 0
            # return_code = pytest.main(files_to_test)
            # return return_code == 0
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error running tests: %s", str(e))
            return False
