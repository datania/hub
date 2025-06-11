# CONTRIBUTING

This file provides guidance to contributors when working with code in this repository.

## Development

Check the [README](README.md) for how to get started. The [Makefile](Makefile) contains common commands to run, lint, test, etc.

## Architecture

Datania is a minimalistic and functional open data platform to help transform and publish Spanish open data

### Data Pipeline Architecture

- Simple and functional scripts.
- Low abstractions, no frameworks.
- Each file is a self-contained dataset.
- Rely on `Makefile` for orchestration.
- Datasets are stored in the `dataset/` directory.

### Minimalistic Example

This is a minimalistic example of a dataset transformation.

```python
import polars as pl
from pathlib import Path

def A(dep: pl.DataFrame) -> pl.DataFrame:
    return dep.with_columns(A = pl.col("x") * 10).select("A")

if __name__ == "__main__":
    dep = pl.read_parquet("data/source.parquet")
    res = A(dep)
    Path("data").mkdir(exist_ok=True)
    res.write_parquet("data/A.parquet", compression="zstd", statistics=True)
    print("✅ A.parquet written")
```

## Environment Variables

Required for full functionality:

- `AEMET_API_TOKEN`: Access token for AEMET weather data API
- `HUGGINGFACE_TOKEN`: Token for publishing datasets to HuggingFace Hub

## Development Notes

- Use `uv` for anything related to Python (running scripts, managing environment, ...)
- Prefer modern libraries like Polars, httpx, DuckDB, ...
- All datasets are designed to be published to HuggingFace Hub
- Make pipelines idempotent, so they can be run multiple times without errors
- Everything versioned in git following "data as code" principles.
