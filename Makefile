.PHONY: install sync serve dev dashboard build test clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -e "."
	cd dashboard && npm install

sync:
	.venv/bin/op sync

serve:
	.venv/bin/uvicorn sahiixx_agency.api.main:app --host 0.0.0.0 --port 8082 --reload

dev:
	@echo "Starting API server..."
	@.venv/bin/uvicorn sahiixx_agency.api.main:app --host 0.0.0.0 --port 8082 &
	@echo "Starting dashboard dev server..."
	@cd dashboard && npm run dev

dashboard:
	cd dashboard && npm run build

mcp:
	.venv/bin/python -m sahiixx_agency.mcp_server.main

test:
	.venv/bin/pytest tests/ -v

clean:
	rm -rf .venv data __pycache__ .pytest_cache dashboard/dist dashboard/node_modules
