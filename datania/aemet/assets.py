import datetime
import os

import dagster as dg
import polars as pl

from datania.aemet.resources import AEMETAPI


@dg.asset()
def raw_estaciones_aemet(aemet_api: AEMETAPI) -> pl.DataFrame:
    """
    Datos de las estaciones meteorológicas de AEMET.
    """

    return pl.DataFrame(aemet_api.get_all_stations())


@dg.asset()
def estaciones_aemet(raw_estaciones_aemet: pl.DataFrame) -> pl.DataFrame:
    """
    Datos procesados de las estaciones meteorológicas de AEMET.
    """

    # Clean latitud and longitud
    def convert_to_decimal(coord):
        degrees = int(coord[:-1][:2])
        minutes = int(coord[:-1][2:4])
        seconds = int(coord[:-1][4:])
        decimal = degrees + minutes / 60 + seconds / 3600
        if coord[-1] in ["S", "W"]:
            decimal = -decimal
        return decimal

    df = raw_estaciones_aemet.with_columns(
        [
            pl.col("latitud").map_elements(convert_to_decimal).alias("latitud"),
            pl.col("longitud").map_elements(convert_to_decimal).alias("longitud"),
        ]
    ).select(
        pl.col("latitud"),
        pl.col("longitud"),
        pl.col("provincia"),
        pl.col("indicativo"),
        pl.col("nombre"),
        pl.col("indsinop")
        .map_elements(lambda x: None if x == "" else x, return_dtype=pl.String)
        .alias("indicativo_sinoptico"),
    )

    return df


@dg.asset()
def raw_datos_meteorologicos_estaciones_aemet(
    context: dg.AssetExecutionContext,
    aemet_api: AEMETAPI,
) -> pl.DataFrame:
    """
    Datos meteorológicos de AEMET de todas las estaciones meteorológicas en España desde 1920.
    """
    if os.getenv("ENVIRONMENT") == "production":
        from_date = datetime.datetime(1920, 1, 1).date()
    else:
        from_date = datetime.date.today() - datetime.timedelta(days=15)

    to_date = datetime.date.today() - datetime.timedelta(days=1)
    context.log.info(f"Fetching data from {from_date} to {to_date}")

    df = pl.DataFrame(aemet_api.get_weather_data(from_date, to_date))
    df = df.with_columns(pl.col("fecha").str.to_date().alias("fecha"))

    return df


@dg.asset()
def datos_meteorologicos_estaciones_aemet(
    raw_datos_meteorologicos_estaciones_aemet: pl.DataFrame,
) -> pl.DataFrame:
    """
    Datos meteorológicos procesados de AEMET de todas las estaciones meteorológicas en España desde 1920.
    """

    return raw_datos_meteorologicos_estaciones_aemet.with_columns(
        pl.col("altitud").cast(pl.Int32, strict=False).alias("altitud")
    )
