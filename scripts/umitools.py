import subprocess
from glob import glob

from dagster_pipes import open_dagster_pipes

with open_dagster_pipes() as context:
    result = subprocess.run(["umi_tools", "--version"], capture_output=True, text=True)
    version = result.stdout.strip()
    context.report_asset_materialization(metadata={"umi_tools_version": version})

    extras = context.extras
    context.log.info(str(extras))
    bc_pattern = context.get_extra("bc_pattern")
    parallel_threads = context.get_extra("parallel_threads")
    # dynamic_command = "'umi_tools extract --bc-pattern=" + bc_pattern + " --stdin={} --stdout=/outputs/$(basename {}) --log=/tmp/$(basename {}).log'"
    # command = ["find", "/inputs", "-name", "\"*.gz\"", "|", "parallel", "-j", f"{parallel_threads}", dynamic_command]

    context.log.info("UmiTools: Started")
    
    find_proc = subprocess.Popen(['find', '/inputs', '-name', '*.gz'], stdout=subprocess.PIPE)
    parallel_cmd = [
        'parallel', '-j', str(parallel_threads),
        f'umi_tools extract --bc-pattern={bc_pattern} --stdin={{}} --stdout=/outputs/{{/}} --log=/tmp/{{/}}.log'
    ]
    output = subprocess.run(parallel_cmd, stdin=find_proc.stdout, capture_output=True, text=True)
    find_proc.stdout.close()

    
    #output = subprocess.run(command, capture_output=True, text=True)
    context.log.info("UmiTools: Completed")
