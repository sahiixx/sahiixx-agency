.PHONY: install setup-dev sync serve dev dashboard build test lint format clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -e "."
	cd dashboard && npm install

setup-dev:
	bash scripts/setup-dev.sh

format:
	black sahiixx_agency tests
	cd dashboard && npm run format

lint:
	ruff check sahiixx_agency tests
	mypy sahiixx_agency
	cd dashboard && npm run lint

sync:
	.venv/bin/op sync

serve:
	.venv/bin/uvicorn sahiixx_agency.api.main:app --host 0.0.0.0 --port 8080 --reload

dev:
	@echo "Starting API server..."
	@.venv/bin/uvicorn sahiixx_agency.api.main:app --host 0.0.0.0 --port 8080 &
	@echo "Starting dashboard dev server..."
	@cd dashboard && npm run dev

dashboard:
	cd dashboard && npm run build

mcp:
	.venv/bin/python -m sahiixx_agency.mcp_server.main

test:
	pytest tests/ -v

clean:
	rm -rf .venv data __pycache__ .pytest_cache dashboard/dist dashboard/node_modules
