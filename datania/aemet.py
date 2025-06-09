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


def _make_api_request_with_retry(client, url, params=None, max_retries=5):
    """Make an API request with exponential backoff retry for rate limiting and server errors."""
    headers = {"Accept-Encoding": "gzip, deflate", "Accept": "application/json"}

    for attempt in range(max_retries):
        try:
            response = client.get(url, params=params, headers=headers)

            if response.status_code == 429:
                # Calculate exponential backoff delay for rate limiting
                delay = (2**attempt) * 2  # 2, 4, 8, 16, 32 seconds
                print(
                    f"  Rate limited (429). Waiting {delay} seconds before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(delay)
                continue
            elif response.status_code == 500:
                # Calculate exponential backoff delay for server errors
                delay = (2**attempt) * 2  # 2, 4, 8, 16, 32 seconds
                print(
                    f"  Server error (500). Waiting {delay} seconds before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(delay)
                continue

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = (2**attempt) * 2
                print(
                    f"  Rate limited (429). Waiting {delay} seconds before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(delay)
                continue
            elif e.response.status_code == 500:
                delay = (2**attempt) * 2
                print(
                    f"  Server error (500). Waiting {delay} seconds before retry {attempt + 1}/{max_retries}..."
                )
                time.sleep(delay)
                continue
            else:
                raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = (2**attempt) * 1  # Shorter delay for other errors
            print(f"  Request failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)

    raise Exception(f"Failed to make API request after {max_retries} attempts")


def download_aemet_stations():
    """Download AEMET station information."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    with httpx.Client(timeout=30.0) as client:
        # Get data URL with retry logic
        response = _make_api_request_with_retry(
            client,
            "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones",
            params={"api_key": api_token},
        )
        data_url = response.json()["datos"]

        # Get stations data with retry logic
        data_response = _make_api_request_with_retry(client, data_url)

        # Handle encoding
        content = data_response.content.decode("latin-1")
        stations = json.loads(content)

    # Save to file
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "aemet_stations.json").write_text(json.dumps(stations, indent=2))

    print(f"Downloaded {len(stations)} stations")


def download_aemet_historical_daily():
    """Download AEMET historical daily climatological data one day at a time starting from 1920."""
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

    day_count = 0
    total_records = 0

    with httpx.Client(timeout=30.0) as client:
        while current_date < end_date:
            # Format date for API (single day)
            date_str = current_date.strftime("%Y-%m-%d")

            # Check if file already exists for this day
            day_file = output_dir / f"{date_str}.json"
            if day_file.exists():
                print(f"Skipping {date_str} (already exists)")
                current_date = current_date + timedelta(days=1)
                continue

            print(f"Downloading data for {date_str}")

            try:
                # Get data URL for daily climatological values with retry logic
                response = _make_api_request_with_retry(
                    client,
                    f"https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{date_str}T00:00:00UTC/fechafin/{date_str}T23:59:59UTC/todasestaciones",
                    params={"api_key": api_token},
                )

                response_data = response.json()

                # Check if we got a valid response with data URL
                if "datos" in response_data:
                    data_url = response_data["datos"]

                    # Get actual data with retry logic
                    data_response = _make_api_request_with_retry(client, data_url)

                    # Handle encoding
                    content = data_response.content.decode("latin-1")
                    day_data = json.loads(content)

                    # Save day data to individual file
                    with open(day_file, "w", encoding="utf-8") as f:
                        json.dump(day_data, f, indent=2, ensure_ascii=False)

                    if day_data:
                        day_count += 1
                        total_records += len(day_data)
                        print(f"  Saved {len(day_data)} records to {day_file.name}")
                    else:
                        print("  No data available for this day, saved empty file")
                else:
                    print(f"  No data URL in response: {response_data}")

            except Exception as e:
                print(f"  Error downloading data for {date_str}: {e}")
                print("  Continuing with next day to avoid data loss...")

            # Move to next day
            current_date = current_date + timedelta(days=1)

            # Add delay between requests to be respectful to the API
            time.sleep(1.0)

            # Progress update every 100 days
            if day_count % 100 == 0 and day_count > 0:
                print(
                    f"Progress: {day_count} days completed, {total_records} total records"
                )

    print(f"Download complete: {day_count} days, {total_records} total records")


if __name__ == "__main__":
    download_aemet_stations()
    download_aemet_historical_daily()
