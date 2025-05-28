import dagster as dg
import polars as pl


@dg.asset(
    retry_policy=dg.RetryPolicy(max_retries=5),
)
def raw_ipc() -> pl.DataFrame:
    """
    Datos de la serie histórica del Índice de Precios de Consumo (IPC) en España en formato CSV.
    """

    df = pl.read_csv(
        "https://www.ine.es/jaxiT3/files/t/csv_bdsc/50904.csv", separator=";"
    )

    return df


@dg.asset()
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


@dg.asset()
def raw_hipotecas_indicadores_por_provincia() -> pl.DataFrame:
    """
    Datos de la serie histórica de Hipotecas en España a nivel de provincia.

    Fuente: https://www.ine.es/dynt3/inebase/es/index.htm?padre=1043
    """
    BASE_URL = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/"

    resultados_urls = [
        {
            "id": 3200,
            "name": "Hipotecas constituidas sobre el total de fincas por naturaleza de la finca",
        },
        {
            "id": 3202,
            "name": "Hipotecas constituidas sobre el total de fincas por entidad que concede el préstamo",
        },
        {
            "id": 3203,
            "name": "Hipotecas constituidas sobre fincas rústicas por entidad que concede el préstamo",
        },
        {
            "id": 3204,
            "name": "Hipotecas constituidas sobre fincas urbanas por entidad que concede el préstamo",
        },
        {
            "id": 3205,
            "name": "Hipotecas con cambios registrales sobre el total de fincas por naturaleza de la finca",
        },
        {
            "id": 3206,
            "name": "Hipotecas con cambios registrales sobre el total de fincas por tipo de cambio",
        },
        {
            "id": 3209,
            "name": "Hipotecas canceladas registralmente sobre el total de fincas por naturaleza de la finca y entidad prestamista",
        },
    ]

    dfs = [
        pl.read_csv(
            BASE_URL + f"{resultado['id']}.csv",
            truncate_ragged_lines=True,
            separator=";",
            infer_schema_length=None,
        )
        for resultado in resultados_urls
    ]

    dfs = [
        df.with_columns(pl.lit(resultado["name"]).alias("Tabla"))
        for df, resultado in zip(dfs, resultados_urls)
    ]

    # Get a list of columns from each dataframe
    column_sets = [set(df.columns) for df in dfs]

    # Find the intersection of all column sets
    common_columns = set.intersection(*column_sets)

    processed_dfs = [
        df.with_columns(
            pl.concat_str(
                [pl.col(i) for i in df.columns if i not in common_columns],
                separator=" - ",
            ).alias("Variable"),
            pl.col("Total").cast(pl.String),
        ).drop(list(set(df.columns) - common_columns))
        for df in dfs
    ]
    # Concatenate all processed dataframes vertically
    combined_df = pl.concat(processed_dfs)

    combined_df = combined_df.with_columns(
        pl.concat_str([pl.col("Tabla"), pl.col("Variable")], separator=" - ").alias(
            "Tabla y Variable"
        )
    ).drop(["Tabla", "Variable"])

    combined_df = combined_df.with_columns(
        pl.col("Total").str.replace_all(r"\.", "").cast(pl.Int64)
    )

    # Convert Periodo from format like "2024M08" to proper dates
    combined_df = combined_df.with_columns(
        pl.col("Periodo")
        .str.replace("M", "-")
        .alias("Periodo")
        .str.strptime(pl.Date, "%Y-%m")
    )

    return combined_df


@dg.asset()
def raw_hipotecas_indicadores_nacionales() -> pl.DataFrame:
    """
    Datos de la serie de indicadores nacionales de Hipotecas en España.
    """

    BASE_URL = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/"

    resultados_urls = [
        {
            "id": 24456,
            "name": "Porcentaje de hipotecas constituidas según tipo de interés",
        },
        {
            "id": 24457,
            "name": "Tipo de interés medio al inicio de las hipotecas constituidas",
        },
        {
            "id": 24458,
            "name": "Plazo medio de las hipotecas constituidas",
        },
    ]

    dfs = [
        pl.read_csv(
            BASE_URL + f"{resultado['id']}.csv",
            truncate_ragged_lines=True,
            separator=";",
            infer_schema_length=None,
        )
        for resultado in resultados_urls
    ]

    dfs = [
        df.with_columns(pl.lit(resultado["name"]).alias("Tabla"))
        for df, resultado in zip(dfs, resultados_urls)
    ]

    common_columns = set(["Periodo", "Total"])

    processed_dfs = [
        df.with_columns(
            pl.concat_str(
                [pl.col(i) for i in df.columns if i not in common_columns],
                separator=" - ",
            ).alias("Variable"),
            pl.col("Total").cast(pl.String),
        ).drop(list(set(df.columns) - common_columns))
        for df in dfs
    ]

    # Concatenate all processed dataframes vertically
    combined_df = pl.concat(processed_dfs)

    combined_df = combined_df.with_columns(
        pl.col("Total")
        .str.replace_all(r"\.", "")
        .str.replace_all(",", ".")
        .cast(pl.Float64)
    )

    combined_df = combined_df.with_columns(
        pl.col("Periodo")
        .str.replace("M", "-")
        .alias("Periodo")
        .str.strptime(pl.Date, "%Y-%m")
    )

    return combined_df


@dg.asset()
def hipotecas(
    raw_hipotecas_indicadores_nacionales: pl.DataFrame,
    raw_hipotecas_indicadores_por_provincia: pl.DataFrame,
) -> pl.DataFrame:
    """
    Datos procesados de Hipotecas en España.
    """

    indicadores_nacionales = raw_hipotecas_indicadores_nacionales.select(
        pl.col("Periodo").alias("fecha"),
        pl.lit("Total Nacional").alias("provincia"),
        pl.col("Variable").alias("variable"),
        pl.col("Total").alias("valor"),
    )

    indicadores_por_provincia = raw_hipotecas_indicadores_por_provincia.select(
        pl.col("Periodo").alias("fecha"),
        pl.col("Provincias").alias("provincia"),
        pl.col("Tabla y Variable").alias("variable"),
        pl.col("Total").alias("valor"),
    )

    df = pl.concat(
        [indicadores_nacionales, indicadores_por_provincia], how="vertical_relaxed"
    )

    return df
