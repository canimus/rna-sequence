import os
from pathlib import Path

import yaml

import dagster as dg

fastqc_job = dg.define_asset_job(
    name="fastqc",
    config=yaml.safe_load(
        open(
            str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "config" / "fastqc.yaml"), "r"
        ).read()
    ),
    selection=dg.AssetSelection.all(),
    description="Run fastqc tool",
)
