from pathlib import Path

import polars as pl


def raw_ipc() -> pl.DataFrame:
    """
    Datos de la serie histórica del Índice de Precios de Consumo (IPC) en España en formato CSV.
    """

    df = pl.read_csv(
        "https://www.ine.es/jaxiT3/files/t/csv_bdsc/50904.csv", separator=";"
    )

    return df


def ipc(raw_ipc: pl.DataFrame) -> pl.DataFrame:
    """
    Datos procesados del Índice de Precios de Consumo (IPC) en España.
    """

    df = raw_ipc.select(
        pl.col("Clases").alias("clase"),
        pl.col("Tipo de dato").alias("tipo_de_dato"),
        pl.col("Periodo").alias("fecha"),
        pl.col("Total").alias("value"),
    )

    df = df.with_columns([
        pl.col("value").cast(pl.Float64, strict=False).alias("value"),
        pl.col("fecha")
        .str.replace("M", "-")
        .str.strptime(pl.Date, format="%Y-%m")
        .alias("fecha"),
    ])

    df = df.filter(pl.col("tipo_de_dato") == "Índice").drop("tipo_de_dato")

    return df


if __name__ == "__main__":
    data_dir = Path("datasets/ipc/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_ipc_data = raw_ipc()
    ipc_data = ipc(raw_ipc_data)

    # Sort by clase, then fecha
    ipc_data = ipc_data.sort(["clase", "fecha"])

    # Write with zstd compression, v2, and statistics
    ipc_data.write_parquet(
        data_dir / "ipc.parquet", compression="zstd", statistics=True
    )
    print("✅ datasets/ipc/data/ipc.parquet written")
