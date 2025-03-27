SHELL := /bin/bash
PYTHON := venv/bin/python
PIP := $(PYTHON) -m pip

# Initialize virtual environment if not already created
init:
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
		$(PIP) install --upgrade pip; \
		echo "Virtual environment initialized."; \
	else \
		echo "Virtual environment already exists."; \
	fi

# Install project dependencies
install: init
	$(PIP) install -r requirements.txt

# Install development dependencies
install-dev: install
	$(PIP) install -r requirements-dev.txt

# Format code using black and isort
format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

# Lint code using pylint
lint:
	$(PYTHON) -m pylint package_updater

# Run tests using pytest
test:
	$(PYTHON) -m pytest tests