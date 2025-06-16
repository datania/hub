.DEFAULT_GOAL := run

.PHONY: .uv
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: setup
setup: .uv
	uv sync --frozen --all-groups

.PHONY: run
run: .uv
	uv run -m datania.ipc
	uv run -m datania.hipotecas
	uv run -m datania.aemet.stations
	uv run -m datania.aemet.daily_weather

upload:
	huggingface-cli upload --repo-type dataset datania/ipc datasets/ipc
	huggingface-cli upload --repo-type dataset datania/hipotecas datasets/hipotecas
	huggingface-cli upload-large-folder --repo-type dataset datania/datos_meteorologicos_estaciones_aemet datasets/datos_meteorologicos_estaciones_aemet

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
