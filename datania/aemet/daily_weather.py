"""Download and process AEMET historical daily weather data."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import polars as pl

BATCH_SIZE = 15  # API maximum


def download_batch(client, api_token, start_date, end_date):
    """Download data for a date range."""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    headers = {"Accept-Encoding": "gzip, deflate", "Accept": "application/json"}

    # Try with retries for rate limiting
    response = None
    for attempt in range(5):
        try:
            response = client.get(
                f"https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/"
                f"fechaini/{start_str}T00:00:00UTC/fechafin/{end_str}T23:59:59UTC/todasestaciones",
                params={"api_key": api_token},
                headers=headers,
            )

            if response.status_code in (429, 500):
                delay = 2 ** (attempt + 1)
                print(f"  Retry {attempt + 1}/5 in {delay}s...")
                time.sleep(delay)
                continue

            response.raise_for_status()
            break

        except Exception:
            if attempt == 4:
                raise
            delay = 2**attempt
            time.sleep(delay)

    if response is None:
        raise Exception("Failed to get response after retries")

    print(response.text)

    response_data = response.json()
    if "datos" not in response_data:
        return None

    # Get actual data
    data_response = client.get(response_data["datos"], headers=headers)
    data_response.raise_for_status()
    content = data_response.content.decode("latin-1")
    return json.loads(content)


def save_daily_files(batch_data, output_dir):
    """Save batch data as individual daily files."""
    if not batch_data:
        return 0

    # Group by date
    daily_data = {}
    for record in batch_data:
        if "fecha" in record:
            date_key = record["fecha"]
            daily_data.setdefault(date_key, []).append(record)

    # Save each day
    saved = 0
    for date_key, records in daily_data.items():
        file_path = output_dir / f"{date_key}.json"
        if not file_path.exists():
            file_path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
            saved += 1

    return saved


def download_historical_daily():
    """Download all historical daily weather data."""
    api_token = os.getenv("AEMET_API_TOKEN")
    if not api_token:
        raise ValueError("AEMET_API_TOKEN environment variable is required")

    output_dir = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "datos_meteorologicos_estaciones_aemet"
        / "data"
        / "raw"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = datetime(1920, 1, 1)
    end_date = datetime.now()
    current_date = start_date

    total_saved = 0

    with httpx.Client(timeout=30.0) as client:
        while current_date < end_date:
            batch_end = min(
                current_date + timedelta(days=BATCH_SIZE - 1),
                end_date - timedelta(days=1),
            )

            # Check if we need this batch
            missing = False
            check_date = current_date
            while check_date <= batch_end:
                if not (
                    output_dir / f"{check_date.strftime('%Y-%m-%d')}.json"
                ).exists():
                    missing = True
                    break
                check_date += timedelta(days=1)

            if missing:
                print(
                    f"Downloading: {current_date.strftime('%Y-%m-%d')} to {batch_end.strftime('%Y-%m-%d')}"
                )

                try:
                    batch_data = download_batch(
                        client, api_token, current_date, batch_end
                    )
                    saved = save_daily_files(batch_data, output_dir)
                    total_saved += saved

                    if saved > 0:
                        print(f"  Saved {saved} days")

                except Exception as e:
                    print(f"  Error: {e}")

                time.sleep(1.5)  # Rate limiting

            current_date = batch_end + timedelta(days=1)

    print(f"✅ Downloaded {total_saved} days total")


def process_to_parquet():
    """Process raw AEMET data files into a single parquet file."""
    base_dir = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "datos_meteorologicos_estaciones_aemet"
    )
    raw_dir = base_dir / "data" / "raw"

    # Read all JSON files
    print("Reading raw data files...")
    all_data = []
    json_files = sorted(raw_dir.glob("*.json"))

    for i, json_file in enumerate(json_files):
        if i % 1000 == 0 and i > 0:
            print(f"  Processing file {i}/{len(json_files)}...")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_data.extend(data)

    print(f"Loaded {len(all_data)} records from {len(json_files)} files")

    # Create DataFrame
    df = pl.DataFrame(all_data)

    # Convert fecha to date type
    df = df.with_columns(pl.col("fecha").str.to_date())

    # Process altitud column
    df = df.with_columns(pl.col("altitud").cast(pl.Int32, strict=False))

    # Convert coordinates if they exist
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

    if "latitud" in df.columns:
        df = df.with_columns(
            pl.col("latitud").map_elements(convert_to_decimal, return_dtype=pl.Float64)
        )
    if "longitud" in df.columns:
        df = df.with_columns(
            pl.col("longitud").map_elements(convert_to_decimal, return_dtype=pl.Float64)
        )

    # Sort by fecha, then indicativo
    df = df.sort(["fecha", "indicativo"])

    # Save to parquet
    output_file = base_dir / "data" / "datos_meteorologicos_estaciones_aemet.parquet"
    df.write_parquet(output_file, compression="zstd", statistics=True)

    print(f"✅ {output_file.relative_to(Path.cwd())} written")
    print(
        f"   {len(df)} records | {df['fecha'].min()} to {df['fecha'].max()} | {df['indicativo'].n_unique()} stations"
    )


if __name__ == "__main__":
    download_historical_daily()
    process_to_parquet()
