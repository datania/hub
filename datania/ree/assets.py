import asyncio
from datetime import datetime, timedelta

import dagster as dg
import httpx
import polars as pl


@dg.asset(retry_policy=dg.RetryPolicy(max_retries=3))
async def raw_demanda_energia_electrica() -> pl.DataFrame:
    """Recolecta datos de demanda de energía eléctrica en España."""
    start_date = datetime(2014, 1, 1)
    end_date = datetime.now() - timedelta(days=1)

    transport = httpx.AsyncHTTPTransport(retries=5)
    limits = httpx.Limits(max_keepalive_connections=2, max_connections=4)
    base_url = "https://apidatos.ree.es/en/datos/"

    async with httpx.AsyncClient(
        transport=transport, limits=limits, base_url=base_url, timeout=60
    ) as client:
        responses = []
        for i in pl.datetime_range(start_date, end_date, "15 d", eager=True):
            request_start_date = i.date().strftime("%Y-%m-%d")
            request_end_date = (i + timedelta(days=15)).date().strftime("%Y-%m-%d")

            params = {
                "start_date": f"{request_start_date}T00:00",
                "end_date": f"{request_end_date}T00:00",
                "time_trunc": "hour",
            }

            response = client.get(
                url="demanda/demanda-tiempo-real",
                params=params,
            )
            responses.append(response)

        gathered = await asyncio.gather(*responses)
        data = [i.json()["included"][0]["attributes"]["values"] for i in gathered]
        exploded_data = [item for sublist in data for item in sublist]

    return pl.from_records(exploded_data).with_columns([
        pl.col("datetime").cast(pl.Datetime),
        pl.col("value").cast(pl.Float64),
    ])


@dg.asset()
def demanda_energia_electrica(
    raw_demanda_energia_electrica: pl.DataFrame,
) -> pl.DataFrame:
    """
    Datos procesados de la demanda de energía eléctrica en España.
    """

    return raw_demanda_energia_electrica
