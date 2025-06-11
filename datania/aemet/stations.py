"""Download AEMET station metadata."""

import json
import os
from pathlib import Path

import httpx


def download_stations():
    """Download and process AEMET station information."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    with httpx.Client(timeout=30.0) as client:
        # Get data URL
        headers = {"Accept-Encoding": "gzip, deflate", "Accept": "application/json"}
        response = client.get(
            "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones",
            params={"api_key": api_token},
            headers=headers,
        )
        response.raise_for_status()
        data_url = response.json()["datos"]

        # Get stations data
        data_response = client.get(data_url, headers=headers)
        data_response.raise_for_status()
        content = data_response.content.decode("latin-1")
        stations = json.loads(content)

    # Convert coordinates
    def convert_to_decimal(coord):
        if not coord or len(coord) < 7:
            return None
        degrees = int(coord[:-1][:2])
        minutes = int(coord[:-1][2:4])
        seconds = int(coord[:-1][4:])
        decimal = degrees + minutes / 60 + seconds / 3600
        if coord[-1] in ["S", "W"]:
            decimal = -decimal
        return decimal

    for station in stations:
        if station.get("latitud"):
            station["latitud"] = convert_to_decimal(station["latitud"])
        if station.get("longitud"):
            station["longitud"] = convert_to_decimal(station["longitud"])

    # Sort by indicativo
    stations.sort(key=lambda x: x.get("indicativo", ""))

    # Save
    data_dir = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "datos_meteorologicos_estaciones_aemet"
        / "data"
    )
    data_dir.mkdir(parents=True, exist_ok=True)

    output_file = data_dir / "estaciones.json"
    output_file.write_text(json.dumps(stations, indent=2, ensure_ascii=False))

    print(f"✅ Downloaded {len(stations)} stations")


if __name__ == "__main__":
    download_stations()
