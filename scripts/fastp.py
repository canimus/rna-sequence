import subprocess
from glob import glob

from dagster_pipes import open_dagster_pipes

with open_dagster_pipes() as context:
    result = subprocess.run(["fastp", "--version"], capture_output=True, text=True)
    version = result.stdout.strip()
    context.report_asset_materialization(metadata={"fastp_tools_version": version})

    extras = context.extras
    context.log.info(str(extras))
    parallel_threads = context.get_extra("parallel_threads")

    context.log.info("FastP: Started")

    find_proc = subprocess.Popen(
        ["find", "/inputs", "-name", "*.gz"], stdout=subprocess.PIPE
    )
    parallel_cmd = [
        "parallel",
        "-j",
        str(parallel_threads),
        f"fastp --trim_front1 3 --length_required 20 -i {{}} -o /outputs/gz/{{/}} --html /outputs/html/{{/}}.html --json /outputs/json/{{/}}.json --thread 1",
    ]
    output = subprocess.run(
        parallel_cmd, stdin=find_proc.stdout, capture_output=True, text=True
    )
    find_proc.stdout.close()

    # output = subprocess.run(command, capture_output=True, text=True)
    context.log.info("FastP: Completed")
