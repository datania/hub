"""
AEMET Open Data API client for downloading climatological data.

This module provides functions to interact with Spain's State Meteorological Agency (AEMET)
Open Data API for downloading historical weather and climatological data.

API Documentation: https://opendata.aemet.es/dist/index.html
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx


def generate_date_ranges(start_year: int = 1920) -> list[tuple[str, str]]:
    """Generate date ranges of max 15 days from start_year to today."""
    ranges: list[tuple[str, str]] = []
    start_date = datetime(start_year, 1, 1)
    end_date = datetime.now()

    current_date = start_date
    while current_date < end_date:
        range_end = min(current_date + timedelta(days=14), end_date)
        ranges.append((
            current_date.strftime("%Y-%m-%d"),
            range_end.strftime("%Y-%m-%d")
        ))
        current_date = range_end + timedelta(days=1)

    return ranges


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, str] | None = None,
    max_retries: int = 3
) -> httpx.Response:
    """Fetch URL with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params)
            _ = response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = 2.0 ** attempt
            await asyncio.sleep(wait_time)

    raise Exception("Max retries exceeded")


async def download_daily_values():
    """Download historical daily climatological values from AEMET."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    # Create output directory
    output_dir = Path("data/valores-climatologicos")
    output_dir.mkdir(parents=True, exist_ok=True)

    date_ranges = generate_date_ranges(1920)
    print(f"Processing {len(date_ranges)} date ranges...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (start_date, end_date) in enumerate(date_ranges):
            output_file = output_dir / f"{start_date}.json"

            # Skip if file already exists
            if output_file.exists():
                print(f"Skipping {start_date} to {end_date} (already exists)")
                continue

            try:
                print(
                    f"Downloading {start_date} to {end_date} "
                    + f"({i+1}/{len(date_ranges)})"
                )

                # Get data URL from API
                api_url = f"https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{start_date}T00:00:00UTC/fechafin/{end_date}T23:59:59UTC/todasestaciones"

                response = await fetch_with_retry(
                    client,
                    api_url,
                    params={"api_key": api_token}
                )

                # Get actual data from the data URL
                response_data = response.json()
                data_url: str = response_data["datos"]
                data_response = await fetch_with_retry(client, data_url)

                # Handle encoding issues - try different encodings
                data = None
                try:
                    data = data_response.json()
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Try different encodings for problematic responses
                    content = None
                    encodings = ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8', 'utf-16']
                    for encoding in encodings:
                        try:
                            content = data_response.content.decode(encoding)
                            data = json.loads(content)
                            break
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue

                    if data is None:
                        raise Exception("Could not decode response with any encoding")

                _ = output_file.write_text(json.dumps(data, indent=2))

                print(f"Saved {len(data)} records to {output_file}")

                # Rate limiting: wait 5 seconds between requests to avoid 429 errors
                await asyncio.sleep(5)

            except Exception as e:
                print(f"Failed to download {start_date} to {end_date}: {e}")
                continue


def download_aemet_stations():
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    with httpx.Client() as client:
        # Get data URL
        response = client.get(
            "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones",
            params={"api_key": api_token},
        )
        _ = response.raise_for_status()

        # Get actual data
        response_data = response.json()
        data_url = response_data["datos"]
        data_response = client.get(data_url)
        _ = data_response.raise_for_status()

        stations = json.loads(data_response.text.encode("utf-8"))

    # Save as JSON
    _ = Path("data").mkdir(exist_ok=True)
    _ = Path("data/aemet_stations.json").write_text(json.dumps(stations, indent=2))

    print(f"Downloaded {len(stations)} stations")


if __name__ == "__main__":
    download_aemet_stations()
    asyncio.run(download_daily_values())
