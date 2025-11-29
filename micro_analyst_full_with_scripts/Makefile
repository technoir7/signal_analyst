PYTHON := python3
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate

.PHONY: venv install test run tmux kill-tmux clean

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating venv in $(VENV)"; \
		$(PYTHON) -m venv $(VENV); \
	else \
		echo "venv already exists"; \
	fi

install: venv
	@echo "Installing requirements..."
	@bash -c "$(ACTIVATE) && pip install --upgrade pip && pip install -r requirements.txt"

test: install
	@echo "Running pytest..."
	@bash -c "$(ACTIVATE) && pytest -v"

run: install
	@echo "Starting micro_analyst on :8000..."
	@bash -c "$(ACTIVATE) && uvicorn agent.micro_analyst:app --reload --port 8000"

tmux: install
	@echo "Starting full tmux cluster..."
	@./run_all_tmux.sh

kill-tmux:
	@echo "Killing tmux session 'micro-analyst'..."
	@tmux kill-session -t micro-analyst 2>/dev/null || echo "No such session."

clean:
	@echo "Cleaning caches..."
	@rm -rf __pycache__ .pytest_cache
