"""
This module provides functions to interact with Spain's State Meteorological Agency (AEMET) Open Data API.

API Documentation: https://opendata.aemet.es/dist/index.html
"""

import json
import os
from pathlib import Path

import httpx


def download_aemet_stations():
    """Download AEMET station information."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    with httpx.Client() as client:
        # Get data URL
        response = client.get(
            "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones",
            params={"api_key": api_token},
        )
        response.raise_for_status()
        data_url = response.json()["datos"]

        # Get stations data
        data_response = client.get(data_url)
        data_response.raise_for_status()

        # Handle encoding
        content = data_response.content.decode("latin-1")
        stations = json.loads(content)

    # Save to file
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    (data_dir / "aemet_stations.json").write_text(json.dumps(stations, indent=2))

    print(f"Downloaded {len(stations)} stations")


if __name__ == "__main__":
    download_aemet_stations()
