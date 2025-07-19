import subprocess
from glob import glob

from dagster_pipes import open_dagster_pipes

with open_dagster_pipes() as context:
    result = subprocess.run(["fastqc", "--version"], capture_output=True, text=True)
    version = result.stdout.strip()
    context.report_asset_materialization(metadata={"fastqc_version": version})

    files = glob("/inputs/**/*.gz")
    pre_command = ["fastqc", "-o", "/outputs", "--threads", "20"]

    context.log.info("FastQC: Started")
    output = subprocess.run(pre_command + files, capture_output=True, text=True)
    context.log.info("FastQC: Completed")
