"""
This module provides functions to interact with Spain's State Meteorological Agency (AEMET) Open Data API.

API Documentation: https://opendata.aemet.es/dist/index.html
"""

import json
import os
import time
from datetime import datetime, timedelta
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
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "aemet_stations.json").write_text(json.dumps(stations, indent=2))

    print(f"Downloaded {len(stations)} stations")


def download_aemet_historical_daily():
    """Download AEMET historical daily climatological data in 15-day batches starting from 1920."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    # Create output directory structure
    output_dir = Path(__file__).parent.parent / "data" / "valores-climatologicos"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Start from 1920-01-01
    start_date = datetime(1920, 1, 1)
    end_date = datetime.now()
    current_date = start_date

    batch_count = 0
    total_records = 0

    with httpx.Client(timeout=30.0) as client:
        while current_date < end_date:
            # Calculate 15-day batch end date
            batch_end = min(current_date + timedelta(days=14), end_date)

            # Format dates for API
            start_str = current_date.strftime("%Y-%m-%d")
            end_str = batch_end.strftime("%Y-%m-%d")

            # Check if file already exists for this batch
            batch_file = output_dir / f"{end_str}.json"
            if batch_file.exists():
                print(f"Skipping {start_str} to {end_str} (already exists)")
                current_date = batch_end + timedelta(days=1)
                continue

            print(f"Downloading data for {start_str} to {end_str}")

            try:
                # Get data URL for daily climatological values
                response = client.get(
                    f"https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{start_str}T00:00:00UTC/fechafin/{end_str}T23:59:59UTC/todasestaciones",
                    params={"api_key": api_token},
                )
                response.raise_for_status()

                response_data = response.json()

                # Check if we got a valid response with data URL
                if "datos" in response_data:
                    data_url = response_data["datos"]

                    # Get actual data
                    data_response = client.get(data_url)
                    data_response.raise_for_status()

                    # Handle encoding
                    content = data_response.content.decode("latin-1")
                    batch_data = json.loads(content)

                    # Save batch data to individual file
                    with open(batch_file, "w", encoding="utf-8") as f:
                        json.dump(batch_data, f, indent=2, ensure_ascii=False)

                    if batch_data:
                        batch_count += 1
                        total_records += len(batch_data)
                        print(f"  Saved {len(batch_data)} records to {batch_file.name}")
                    else:
                        print("  No data available for this period, saved empty file")
                else:
                    print(f"  No data URL in response: {response_data}")

            except Exception as e:
                print(f"  Error downloading batch {start_str} to {end_str}: {e}")

            # Move to next batch
            current_date = batch_end + timedelta(days=1)

            # Add delay between requests to be respectful to the API
            time.sleep(0.5)

            # Progress update every 50 batches
            if batch_count % 50 == 0 and batch_count > 0:
                print(
                    f"Progress: {batch_count} batches completed, {total_records} total records"
                )

    print(f"Download complete: {batch_count} batches, {total_records} total records")


if __name__ == "__main__":
    download_aemet_stations()
    download_aemet_historical_daily()
