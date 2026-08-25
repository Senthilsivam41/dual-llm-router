# Dual-LLM Router — developer commands (portfolio.dev contract)

.PHONY: setup bootstrap doctor demo dev format lint typecheck test build check clean help

PYTHON ?= python3
UV ?= uv

help:
	@echo "Portfolio commands:"
	@echo "  make setup      Install locked dependencies"
	@echo "  make bootstrap  Setup + reset local evolution state"
	@echo "  make doctor     Diagnose runtimes/config (no secrets)"
	@echo "  make demo       Deterministic simulate benchmark (no API key)"
	@echo "  make dev        Interactive smoke: list tasks + easy simulate"
	@echo "  make check      Non-mutating quality gate (pytest subset)"
	@echo "  make test       Full pytest suite"
	@echo "  make clean      Remove documented generated output only"

setup:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) sync; \
	else \
		$(PYTHON) -m pip install -r requirements.txt; \
		$(PYTHON) -m pip install -e .; \
	fi

bootstrap: setup
	$(PYTHON) scripts/reset.py

doctor:
	@echo "=== dual-llm-router doctor ==="
	@command -v $(PYTHON) >/dev/null && $(PYTHON) --version || echo "MISSING: python3"
	@command -v $(UV) >/dev/null && $(UV) --version || echo "OPTIONAL: uv not installed (pip fallback OK)"
	@test -f pyproject.toml && echo "OK: pyproject.toml" || echo "MISSING: pyproject.toml"
	@test -f portfolio.yaml && echo "OK: portfolio.yaml" || echo "MISSING: portfolio.yaml"
	@test -f .env.example && echo "OK: .env.example" || echo "MISSING: .env.example"
	@if [ -n "$${OPENROUTER_API_KEY:-}" ]; then echo "OK: OPENROUTER_API_KEY is set (value hidden)"; \
	else echo "INFO: OPENROUTER_API_KEY unset — demo/check use --simulate"; fi
	@test -d .autoclaw && echo "INFO: .autoclaw/ present (local runtime)" || echo "INFO: .autoclaw/ absent (run make bootstrap)"
	@test -d .codegraph && echo "INFO: .codegraph/ present" || echo "INFO: .codegraph/ absent (optional: codegraph init)"

demo:
	$(PYTHON) scripts/reset.py
	$(PYTHON) scripts/benchmark_runner.py --suite easy --variant hermes_v1,laguna_v1 --simulate
	$(PYTHON) scripts/benchmark_dashboard.py --report overall

dev:
	$(PYTHON) scripts/reset.py
	$(PYTHON) scripts/benchmark_runner.py --suite easy --simulate --list
	$(PYTHON) scripts/benchmark_runner.py --suite easy --variant hermes_v1,laguna_v1 --simulate

format:
	@echo "No formatter configured yet (Ruff planned)."

lint:
	@echo "No linter configured yet (Ruff planned)."

typecheck:
	@echo "No typecheck gate configured yet (pyright/mypy planned)."

test:
	$(PYTHON) -m pytest tests/ -q --ignore=tests/test_p1_functionality.py

build:
	@echo "Library product — no distributable build step; use pip/uv install."

check:
	$(PYTHON) -m pytest \
		tests/test_scoring.py \
		tests/test_mutation.py \
		tests/test_ab_test.py \
		tests/test_evolution.py \
		tests/test_benchmark.py \
		tests/test_benchmark_publisher.py \
		tests/test_p0_security.py -q

clean:
	rm -rf .pytest_cache reports/
	@echo "Left .autoclaw/, .venv/, and workspace/ intact (runtime state)."
