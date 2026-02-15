.PHONY: run-backend run-ui venv update-venv help

# Get the absolute path to the project root
ROOT_DIR := $(shell pwd)

# Default ports
BACKEND_PORT ?= 8000
UI_PORT ?= 8080

# Backend URL for UI proxy
BACKEND_URL = http://127.0.0.1:$(BACKEND_PORT)

# Virtual environment and config paths (can be overridden)
VENV_PATH ?= $(ROOT_DIR)/backend/.venv
TELESCOPE_CONFIG ?= $(ROOT_DIR)/dev/config.yaml

help:
	@echo "Available commands:"
	@echo "  make venv                              - Create virtual environment and install dependencies"
	@echo "  make update-venv                       - Update dependencies in existing virtual environment"
	@echo "  make run-backend [BACKEND_PORT=8000]   - Run Django backend server"
	@echo "  make run-ui [UI_PORT=8080] [BACKEND_PORT=8000]  - Run Vue.js UI dev server"
	@echo ""
	@echo "Environment variables:"
	@echo "  BACKEND_PORT        - Backend server port (default: 8000)"
	@echo "  UI_PORT             - UI dev server port (default: 8080)"
	@echo "  VENV_PATH           - Path to virtual environment (default: backend/.venv)"
	@echo "  TELESCOPE_CONFIG    - Path to config file (default: dev/config.yaml)"
	@echo ""
	@echo "Examples:"
	@echo "  make venv"
	@echo "  make update-venv"
	@echo "  make run-backend"
	@echo "  make run-backend BACKEND_PORT=8999"
	@echo "  make run-ui"
	@echo "  make run-ui UI_PORT=8888 BACKEND_PORT=8999"

venv:
	@echo "Creating virtual environment at $(VENV_PATH)..."
	@if [ -d "$(VENV_PATH)" ]; then \
		echo "Virtual environment already exists at $(VENV_PATH)"; \
		exit 1; \
	fi
	python3 -m venv $(VENV_PATH)
	@echo "Installing dependencies..."
	$(VENV_PATH)/bin/pip install --upgrade pip
	$(VENV_PATH)/bin/pip install -r backend/requirements.txt
	@if [ -f "backend/requirements-dev.txt" ]; then \
		echo "Installing dev dependencies..."; \
		$(VENV_PATH)/bin/pip install -r backend/requirements-dev.txt; \
	fi
	@echo ""
	@echo "Virtual environment created successfully!"
	@echo "To activate it manually: source $(VENV_PATH)/bin/activate"

update-venv:
	@echo "Updating virtual environment at $(VENV_PATH)..."
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "Error: Virtual environment not found at $(VENV_PATH)"; \
		echo "Please create it first with: make venv"; \
		exit 1; \
	fi
	@echo "Upgrading pip..."
	$(VENV_PATH)/bin/pip install --upgrade pip
	@echo "Installing/updating dependencies from requirements.txt..."
	$(VENV_PATH)/bin/pip install --upgrade -r backend/requirements.txt
	@if [ -f "backend/requirements-dev.txt" ]; then \
		echo "Installing/updating dev dependencies..."; \
		$(VENV_PATH)/bin/pip install --upgrade -r backend/requirements-dev.txt; \
	fi
	@echo ""
	@echo "Virtual environment updated successfully!"

run-backend:
	@echo "Starting backend on port $(BACKEND_PORT)..."
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "Error: Virtual environment not found at $(VENV_PATH)"; \
		echo "Please create it with: make venv"; \
		exit 1; \
	fi
	@if command -v direnv >/dev/null 2>&1 && [ -f backend/.envrc ]; then \
		cd backend && direnv exec . sh -c 'echo "Using config: $$TELESCOPE_CONFIG_FILE" && python manage.py runserver 127.0.0.1:$(BACKEND_PORT)'; \
	else \
		source $(VENV_PATH)/bin/activate && \
		export TELESCOPE_CONFIG_FILE=$(TELESCOPE_CONFIG) && \
		cd backend && \
		echo "Using config: $$TELESCOPE_CONFIG_FILE" && \
		python manage.py runserver 127.0.0.1:$(BACKEND_PORT); \
	fi

run-ui:
	@echo "Starting UI on port $(UI_PORT) with backend proxy at $(BACKEND_URL)..."
	cd ui && \
	VUE_APP_BACKEND_URL=$(BACKEND_URL) npm run serve -- --port $(UI_PORT)
