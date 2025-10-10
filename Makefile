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
	@echo "  status    - Toon database statistieken"
	@echo "  search    - Zoek en indexeer papers van arXiv"
	@echo "  download  - Download PDFs voor geïndexeerde papers"
	@echo "  convert   - Converteer PDFs naar Markdown"
	@echo "  llm       - Voer LLM kwaliteitscontrole uit"
	@echo "  pipeline  - Voer volledige pipeline uit (alle stappen)"
	@echo "  import    - Importeer metadata JSON met schema-validatie"
	@echo "  prepare   - Maak papers aan op basis van metadata"
	@echo "  seed-labels - Seed labels en questions vanuit data/labels.json"
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@echo "  test      - Voer unit tests uit"
	@echo "  lint      - Voer code linting uit"
	@echo "  format    - Formatteer code met black"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make refresh   # Reset omgeving en installeer dependencies"
	@echo "  make status    # Check huidige status"
	@echo "  make search    # Alleen nieuwe papers zoeken"
	@echo "  make pipeline  # Volledige workflow"

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

# Pipeline stappen
.PHONY: status
status: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📊 Checking database status...$(NC)"
	$(VENV_PYTHON) -c "from src.main import print_stats; print_stats()"

.PHONY: search
search: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🔍 Starting paper search and indexing...$(NC)"
	$(VENV_PYTHON) -c "import logging.config, logging; from src.config import LOGGING_CONFIG; logging.config.dictConfig(LOGGING_CONFIG); from src.database import PaperDatabase; from src.arxiv_client import ArxivClient; from src.main import search_and_index_papers; logger=logging.getLogger('src'); db=PaperDatabase(); client=ArxivClient(); search_and_index_papers(db, client, logger)"

.PHONY: download
download: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)⬇️  Starting PDF downloads...$(NC)"
	$(VENV_PYTHON) -c "import logging.config, logging; from src.config import LOGGING_CONFIG; logging.config.dictConfig(LOGGING_CONFIG); from src.database import PaperDatabase; from src.arxiv_client import ArxivClient; from src.main import download_pdfs; logger=logging.getLogger('src'); db=PaperDatabase(); client=ArxivClient(); download_pdfs(db, client, logger)"

.PHONY: convert
convert: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📝 Starting PDF to Markdown conversion...$(NC)"
	$(VENV_PYTHON) -c "import logging.config, logging; from src.config import LOGGING_CONFIG; logging.config.dictConfig(LOGGING_CONFIG); from src.database import PaperDatabase; from src.main import convert_to_markdown; logger=logging.getLogger('src'); db=PaperDatabase(); convert_to_markdown(db, logger)"

.PHONY: llm
llm: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🤖 Starting LLM quality check...$(NC)"
	@echo "$(YELLOW)💡 Note: LLM requires Ollama server running$(NC)"
	$(VENV_PYTHON) -c "import logging.config, logging; from src.config import LOGGING_CONFIG; logging.config.dictConfig(LOGGING_CONFIG); from src.database import PaperDatabase; from src.llm import LLMChecker; from src.main import llm_quality_check; logger=logging.getLogger('src'); db=PaperDatabase(); checker=LLMChecker(); llm_quality_check(db, checker, logger)"

.PHONY: pipeline
pipeline: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🚀 Starting complete pipeline...$(NC)"
	$(VENV_PYTHON) -m src.main

.PHONY: import
import: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)📥 Importing metadata...$(NC)"
	@if [ -z "$(MAX)" ] && [ -z "$(BATCH)" ]; then \
		$(VENV_PYTHON) -c "from src.main import run_metadata_import; run_metadata_import()"; \
	else \
		ARGS=""; \
		if [ -n "$(MAX)" ]; then ARGS="max_records=int('$(MAX)')"; fi; \
		if [ -n "$(BATCH)" ]; then \
		  if [ -n "$$ARGS" ]; then ARGS="$$ARGS, "; fi; \
		  ARGS="$$ARGS batch_size=int('$(BATCH)')"; \
		fi; \
		$(VENV_PYTHON) -c "from src.main import run_metadata_import; run_metadata_import($$ARGS)"; \
	fi

.PHONY: prepare
prepare: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🧩 Preparing paper records from metadata...$(NC)"
	@if [ -z "$(BATCH)" ] && [ -z "$(LIMIT)" ]; then \
		$(VENV_PYTHON) -c "from src.main import run_paper_preparation; run_paper_preparation()"; \
	else \
		ARGS=""; \
		if [ -n "$(BATCH)" ]; then ARGS="batch_size=int('$(BATCH)')"; fi; \
		if [ -n "$(LIMIT)" ]; then \
		  if [ -n "$$ARGS" ]; then ARGS="$$ARGS, "; fi; \
		  ARGS="$$ARGS limit=int('$(LIMIT)')"; \
		fi; \
		$(VENV_PYTHON) -c "from src.main import run_paper_preparation; run_paper_preparation($$ARGS)"; \
	fi

.PHONY: seed-labels
seed-labels: $(VENV_DIR)/bin/activate
	@echo "$(BLUE)🌱 Seeding labels and questions...$(NC)"
	@if [ -z "$(LABELS)" ]; then \
		$(VENV_PYTHON) -c "from src.main import seed_labels_questions; seed_labels_questions()"; \
	else \
		$(VENV_PYTHON) -c "from src.main import seed_labels_questions; seed_labels_questions(labels_path='$(LABELS)')"; \
	fi

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

.PHONY: install-ollama
install-ollama:
	@echo "$(BLUE)🤖 Installing Ollama...$(NC)"
	@echo "$(YELLOW)💡 This will download and install Ollama locally$(NC)"
	curl -fsSL https://ollama.ai/install.sh | sh
	@echo "$(GREEN)✅ Ollama installed$(NC)"
	@echo "$(YELLOW)💡 Run 'ollama pull llama3.2' to download the model$(NC)"

.PHONY: setup-ollama
setup-ollama:
	@echo "$(BLUE)🤖 Setting up Ollama model...$(NC)"
	ollama pull llama3.2
	@echo "$(GREEN)✅ Ollama model ready$(NC)"
	@echo "$(YELLOW)💡 Enable LLM in src/config.py: LLM_CONFIG['enabled'] = True$(NC)"

# Debugging en monitoring
.PHONY: logs
logs:
	@echo "$(BLUE)📋 Showing recent logs...$(NC)"
	@if [ -f metastudy.log ]; then \
		tail -50 metastudy.log; \
	else \
		echo "$(YELLOW)No log file found. Run a pipeline step first.$(NC)"; \
	fi

.PHONY: data-info
data-info:
	@echo "$(BLUE)📁 Data directory information:$(NC)"
	@echo "Database:"
	@ls -la data/*.db 2>/dev/null || echo "  No database files found"
	@echo "PDFs:"
	@ls -la data/pdf/ 2>/dev/null | wc -l | xargs -I {} echo "  {} PDF files"
	@echo "Markdown:"
	@ls -la data/md/ 2>/dev/null | wc -l | xargs -I {} echo "  {} Markdown files"

# Combinatie targets voor workflows
.PHONY: search-download
search-download: search download

.PHONY: download-convert
download-convert: download convert

.PHONY: convert-llm  
convert-llm: convert llm

.PHONY: full-processing
full-processing: download convert llm

# Safety checks
.PHONY: check-ollama
check-ollama:
	@echo "$(BLUE)🔍 Checking Ollama status...$(NC)"
	@if command -v ollama >/dev/null 2>&1; then \
		echo "$(GREEN)✅ Ollama is installed$(NC)"; \
		if pgrep -f ollama >/dev/null; then \
			echo "$(GREEN)✅ Ollama service is running$(NC)"; \
			ollama list 2>/dev/null || echo "$(YELLOW)⚠️  No models installed$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Ollama service is not running$(NC)"; \
		fi \
	else \
		echo "$(RED)❌ Ollama is not installed$(NC)"; \
		echo "$(YELLOW)💡 Run 'make install-ollama' to install$(NC)"; \
	fi
