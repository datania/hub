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


def _make_api_request_with_retry(client, url, params=None, max_retries=8):
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


def _download_batch_data(client, api_token, start_date, end_date):
    """Download data for a date range and return parsed JSON data."""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    response = _make_api_request_with_retry(
        client,
        f"https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{start_str}T00:00:00UTC/fechafin/{end_str}T23:59:59UTC/todasestaciones",
        params={"api_key": api_token},
    )

    response_data = response.json()
    if "datos" not in response_data:
        return None

    data_response = _make_api_request_with_retry(client, response_data["datos"])
    content = data_response.content.decode("latin-1")
    return json.loads(content)


def _save_batch_data_as_daily_files(batch_data, output_dir):
    """Save batch data as individual daily files, grouped by date."""
    if not batch_data:
        return 0, 0

    daily_data = {}
    for record in batch_data:
        if "fecha" in record:
            date_key = record["fecha"]
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(record)

    day_count = total_records = 0
    for date_key, day_records in daily_data.items():
        day_file = output_dir / f"{date_key}.json"
        if day_file.exists():
            continue

        with open(day_file, "w", encoding="utf-8") as f:
            json.dump(day_records, f, indent=2, ensure_ascii=False)

        day_count += 1
        total_records += len(day_records)
        print(f"  Saved {len(day_records)} records to {day_file.name}")

    return day_count, total_records


def download_aemet_historical_daily_batch():
    """Download AEMET historical daily climatological data using 15-day batch requests."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    output_dir = Path(__file__).parent.parent / "data" / "valores-climatologicos"
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = datetime(1920, 1, 1)
    end_date = datetime.now()
    current_date = start_date
    batch_size = 15  # API maximum

    day_count = total_records = 0

    with httpx.Client(timeout=30.0) as client:
        while current_date < end_date:
            batch_end = min(
                current_date + timedelta(days=batch_size - 1),
                end_date - timedelta(days=1),
            )
            print(
                f"Downloading batch: {current_date.strftime('%Y-%m-%d')} to {batch_end.strftime('%Y-%m-%d')}"
            )

            try:
                batch_data = _download_batch_data(
                    client, api_token, current_date, batch_end
                )
                if batch_data:
                    batch_days, batch_records = _save_batch_data_as_daily_files(
                        batch_data, output_dir
                    )
                    day_count += batch_days
                    total_records += batch_records
                    print(f"  Complete: {batch_days} days, {batch_records} records")
                else:
                    print("  No data available")
            except Exception as e:
                print(f"  Error: {e}")
                print("  Continuing...")

            current_date = batch_end + timedelta(days=1)
            time.sleep(1.5)

            if day_count > 0 and day_count % 150 == 0:  # Every 10 batches
                print(f"Progress: {day_count} days, {total_records} records")

    print(f"Complete: {day_count} days, {total_records} records")


if __name__ == "__main__":
    download_aemet_stations()
    download_aemet_historical_daily_batch()
