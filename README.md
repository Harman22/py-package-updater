# Python Package Updater

A tool to automatically update Python packages while verifying tests pass.

## Features

- Detects packages from requirements.txt or Pipfile
- Finds and runs tests with 'test_' prefix
- Creates isolated testing environments
- Generates update reports
- Safely updates package versions

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m package_updater /path/to/your/project
```

## Requirements

- Python 3.8+
- virtualenv
- pytest

## License

MIT 