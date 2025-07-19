from dagster_docker import PipesDockerClient

import dagster as dg

from . import assets as A
from .jobs import fastqc_job

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([A]),
    jobs=[fastqc_job],
    resources={"docker_client": PipesDockerClient()},
)
