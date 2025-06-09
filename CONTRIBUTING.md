# CONTRIBUTING

This file provides guidance to contributors when working with code in this repository. The README provides more information about the project.

## Architecture

The project main pipelines are defined in `datania/`
Each file is a different pipeline, orchestrated by a Makefile
The Makefile contains common commands for development and data processing

## Environment Variables

Required for full functionality:

- `AEMET_API_TOKEN`: Access token for AEMET weather data API
- `HUGGINGFACE_TOKEN`: Token for publishing datasets to HuggingFace Hub

## Development Notes

- Use `uv` for dependency management and Python environment
- Prefer modern libraries like Polars, httpx, DuckDB, ...
- All datasets are designed to be published to HuggingFace Hub
- Make pipelines idempotent, so they can be run multiple times without errors
