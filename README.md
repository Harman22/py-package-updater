# Python Package Updater

![Supported Python Versions](https://img.shields.io/badge/python-3.8%2B-blue)

Python Package Updater is a robust tool designed to streamline the process of updating Python package dependencies in your projects. Keeping your dependencies up-to-date is crucial for maintaining security, performance, and compatibility with the latest features. However, this process can often be tedious and error-prone, especially when dealing with complex projects or multiple dependencies.

This tool automates the entire workflow of dependency updates, from detecting outdated packages to validating their compatibility through testing. By leveraging isolated virtual environments and automated test discovery, Python Package Updater ensures that updates are applied safely without breaking your project.

## Features

- **Dependency Detection**: Automatically detects dependencies from `requirements.txt` or `Pipfile`.
- **Test Discovery**: Finds and runs tests with the `test_` prefix or pytest decorators.
- **Isolated Testing**: Creates isolated virtual environments to test updates without affecting your system environment.
- **Update Analysis**: Analyzes available package updates and determines compatibility.
- **Safe Updates**: Ensures updates are applied only if all tests pass.
- **Customizable Options**: Allows you to specify packages to update, perform dry runs, or skip tests based on your requirements.

## Architecture Diagram

![Architecture Diagram](https://raw.githubusercontent.com/Harman22/py-package-updater/refs/heads/main/assets/flow.drawio.png)

## Installation

Clone the repository and initialize the virtual environment:

```bash
git clone https://github.com/Harman22/py-package-updater.git
cd py_package_updater
make init
```

## Usage

You can use the tool either via `Makefile` commands or directly through the CLI.

### Using Makefile Commands

- **Initialize the environment**:
  ```bash
  make init
  ```

- **Install dependencies**:
  ```bash
  make install
  ```

- **Install development dependencies**:
  ```bash
  make install-dev
  ```

- **Format the code**:
  ```bash
  make format
  ```
  
- **Lint the code**:
  ```bash
  make lint
  ```
  
- **Run tests**:
  ```bash
  make test
  ```
  
### Using CLI Options

Run the tool directly on your Python project directory:

```bash
python -m py_package_updater /path/to/your/project
```

#### Command-Line Options

- `--packages`: Specify specific packages to update (default: all packages).
- `--dry-run`: Run without making any changes.
- `--verbose`: Show detailed output.
- `--skip-tests`: Skip running tests (not recommended).
- `--test-folder`: Path to the folder containing test files (default: project root).

#### Examples

Update all packages in the current directory:

```bash
python -m py_package_updater .
```

Update specific packages:

```bash
python -m py_package_updater . --packages requests pytest
```

Perform a dry run to preview changes:

```bash
python -m py_package_updater . --dry-run
```

Run tests from a specific folder:

```bash
python -m py_package_updater . --test-folder tests
```

## Requirements

- Python 3.8+
- `virtualenv`
- `pytest`
- `requests`
- `packaging`

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
   - Run the tests to ensure your changes do not break existing functionality.
   - Lint your code to ensure it adheres to the project's coding standards.
   - Format your code to maintain consistency.
3. Commit your changes and push them to your fork.
4. Submit a pull request with a detailed description of your changes.

## Support

If you encounter any issues or have questions, feel free to open an issue on the [GitHub repository](https://github.com/Harman22/py-package-updater).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.