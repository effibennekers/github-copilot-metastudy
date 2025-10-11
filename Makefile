# GitHub Copilot Metastudy Makefile
# Maakt het mogelijk om pipeline stappen afzonderlijk uit te voeren

# Variabelen
PYTHON = python3
VENV_DIR = venv
VENV_PYTHON = $(VENV_DIR)/bin/python

# Kleuren voor output
GREEN = \033[0;32m
BLUE = \033[0;34m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Default target
.PHONY: help
help:
	@echo "$(BLUE)GitHub Copilot Metastudy Pipeline$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(GREEN)Setup Commands:$(NC)"
	@echo "  refresh   - Verwijder logs/caches, reset venv en installeer dependencies"
	@echo ""
	@echo "$(GREEN)Pipeline Commands:$(NC)"
	@echo "  import-labels     - Seed labels en questions vanuit data/labels.json"
	@echo "  import-metadata   - Importeer metadata JSON met schema-validatie"
	@echo "  run-labeling      - Verwerk labeling_queue (default: JOBS=10)"
	@echo "  prepare-labeling  - Vul labeling_queue (default: date_after=2025-09-01)"
	@echo "  list-questions    - Toon alle questions met labelnaam"
	@echo "  prepare-download  - Vul download_queue op basis van label"
	@echo "  status            - Toon database statistieken"
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@echo "  format    - Formatteer code met black"
	@echo "  lint      - Voer code linting uit"
	@echo "  test      - Voer unit tests uit"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make refresh          # Reset omgeving en installeer dependencies"
	@echo "  make status           # Check huidige status"
	@echo "  make import-metadata  # Metadata importeren met validatie"
	@echo "  make run-labeling        # Verwerk 10 labeling jobs (default)"
	@echo "  make run-labeling JOBS=5 # Verwerk 5 labeling jobs"
	@echo "  make prepare-labeling Q=42 # Queue labeling jobs na 2025-09-01 voor vraag 42"
	@echo "  make list-questions   # Toon alle questions"

# Setup en installatie
.PHONY: refresh
refresh:
	@echo "$(BLUE)🔄 Refreshing environment (logs, caches, venv, deps)...$(NC)"
	@echo "$(YELLOW)🧹 Removing old logs and caches...$(NC)"
	@rm -f metastudy.log 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(YELLOW)🔁 Resetting virtual environment...$(NC)"
	@rm -rf $(VENV_DIR)
	@$(MAKE) $(VENV_DIR)/bin/activate
	@echo "$(GREEN)✅ Refresh completed successfully!$(NC)"
	@echo "$(YELLOW)💡 Run 'make status' to check current database status$(NC)"

$(VENV_DIR)/bin/activate: requirements.txt
	@echo "$(BLUE)🔧 Setting up virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $(VENV_DIR)/bin/activate

.PHONY: status
status: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📊 Checking database status...$(NC)"
	$(VENV_PYTHON) -m src.main stats

.PHONY: import-metadata
import-metadata: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📥 Importing metadata...$(NC)"
	@if [ -z "$(MAX)" ] && [ -z "$(BATCH)" ]; then \
		$(VENV_PYTHON) -m src.main import-metadata; \
	else \
		ARGS=""; \
		if [ -n "$(MAX)" ]; then ARGS="$$ARGS --max-records $(MAX)"; fi; \
		if [ -n "$(BATCH)" ]; then ARGS="$$ARGS --batch-size $(BATCH)"; fi; \
		$(VENV_PYTHON) -m src.main import-metadata $$ARGS; \
	fi


.PHONY: prepare-labeling
prepare-labeling: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🗂️  Preparing labeling queue...$(NC)"
	@if [ -z "$(Q)" ]; then \
		echo "$(RED)❌ Provide question id via Q=<id>$(NC)"; exit 1; \
	fi
	@if [ -z "$(DATE)" ]; then DATE=2025-09-01; else DATE=$(DATE); fi; \
	$(VENV_PYTHON) -m src.main prepare-labeling $$Q --date-after $$DATE

.PHONY: import-labels
import-labels: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🌱 Seeding labels and questions...$(NC)"
	$(VENV_PYTHON) -m src.main import-labels

# Prepare download_queue op basis van label
.PHONY: prepare-download
prepare-download: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📥 Preparing download queue from label...$(NC)"
	@if [ -z "$(L)" ]; then \
		echo "$(RED)❌ Provide label id via L=<id>$(NC)"; exit 1; \
	fi
	$(VENV_PYTHON) -m src.main prepare-download $$L

# Development commands
.PHONY: test
test: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🧪 Running unit tests...$(NC)"
	$(VENV_PYTHON) -m pytest src/tests/ -v

.PHONY: lint
lint: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🔍 Running code linting...$(NC)"
	$(VENV_PYTHON) -m flake8 src/ --max-line-length=100 --ignore=E203,W503

.PHONY: format
format: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)✨ Formatting code with black...$(NC)"
	$(VENV_PYTHON) -m black src/ --line-length=100

# Utility commands
.PHONY: run-labeling
run-labeling: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🏷️  Running labeling jobs...$(NC)"
	@if [ -z "$(JOBS)" ]; then JOBS=10; else JOBS=$(JOBS); fi; \
	$(VENV_PYTHON) -m src.main label --jobs $$JOBS


.PHONY: list-questions
list-questions: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)❓ Listing questions...$(NC)"
	@$(VENV_PYTHON) -m src.main list-questions

.PHONY: run-download
run-download: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)⬇️  Running downloads from download_queue...$(NC)"
	@if [ -z "$(N)" ]; then \
		$(VENV_PYTHON) -m src.main run-download; \
	else \
		$(VENV_PYTHON) -m src.main run-download --limit $(N); \
	fi

