.DEFAULT_GOAL := run

.PHONY: .uv
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: setup
setup: .uv
	uv sync --frozen --all-groups

.PHONY: run
run: .uv
	uv run -m datania.hipotecas

upload:
	huggingface-cli upload --repo-type dataset datania/hipotecas datasets/hipotecas

.PHONY: web
web:
	uv run python -m http.server 8000 --directory web

.PHONY: lint
lint:
	uv run ruff check
	uv run ty check

.PHONY: clean
clean:
	rm -rf data/*.parquet
