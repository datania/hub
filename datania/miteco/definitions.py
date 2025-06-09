import dagster as dg

from datania.miteco import assets
from datania.miteco.resources import MITECOArcGisAPI

definitions = dg.Definitions(
    assets=dg.load_assets_from_modules([assets]),
    resources={"miteco_api": MITECOArcGisAPI()},
)
