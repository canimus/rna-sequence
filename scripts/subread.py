import subprocess
from glob import glob

from dagster_pipes import open_dagster_pipes

with open_dagster_pipes() as context:
    result = subprocess.run(
        ["featureCounts", "-v"],
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip()
    version_err = result.stderr.strip()
    # context.log.info(str(version))
    context.log.info(str(version_err))
    # context.report_asset_materialization(metadata={"bowtie2_tools_version": version})

    # extras = context.extras
    # context.log.info(str(extras))
    # bc_pattern = context.get_extra("bc_pattern")
    # parallel_threads = context.get_extra("parallel_threads")

    context.log.info("FeatureCounts: Started")

    # find_proc = subprocess.Popen(
    #     ["find", "/inputs", "-name", "*.fasta"], stdout=subprocess.PIPE
    # )
    # parallel_cmd = [
    #     "parallel",
    #     "-j",
    #     str(parallel_threads),
    #     f"bowtie2-build -f {{}} /outputs/{{/}}",
    # ]
    # output = subprocess.run(
    #     parallel_cmd, stdin=find_proc.stdout, capture_output=True, text=True
    # )
    # find_proc.stdout.close()

    # output = subprocess.run(command, capture_output=True, text=True)
    context.log.info("FeatureCounts: Completed")
