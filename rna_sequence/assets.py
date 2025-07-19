import hashlib
import os
from glob import glob
from pathlib import Path
from typing import Iterator, List, Tuple

from dagster_docker import PipesDockerClient

import dagster as dg


class FolderConfig(dg.Config):
    input_pattern: str = "MD5.txt"
    input_folder: str = "/inputs"

    output_pattern: str = "*.gz"
    output_folder: str = "/outputs"


@dg.asset(
    check_specs=[
        dg.AssetCheckSpec(
            name="files_found",
            description="Validates existance of md5 files",
            asset="fasta_md5",
        )
    ]
)
def fasta_md5(
    context: dg.AssetExecutionContext, config: FolderConfig
) -> Iterator[dg.Output[List[Tuple[str, str]]]]:
    """Retrive MD5 files"""
    files: List[str] = glob(
        str(Path(config.input_folder) / "**" / config.input_pattern)
    )
    pairs = []
    for file in files:
        with open(file, "r") as fd:
            for line in fd.readlines():
                pair = tuple(line.strip().split())
                context.log.info(pair)
                pairs.append(pair)

    yield dg.AssetCheckResult(passed=len(pairs) > 0, check_name="files_found")

    yield dg.Output(value=pairs, metadata={"dagster/num_rows": len(pairs)})


@dg.asset(
    check_specs=[
        dg.AssetCheckSpec(
            name="files_found",
            description="Validates existance of gz files",
            asset="fasta_gz",
        )
    ]
)
def fasta_gz(
    context: dg.AssetExecutionContext, config: FolderConfig
) -> Iterator[dg.Output[List[Tuple[str, str]]]]:
    """Retrive GZ files"""

    def md5_file(filepath):
        """Compute MD5 hash of a file in chunks."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    files = glob(str(Path(config.input_folder) / "**" / config.input_pattern))
    context.log.info(str(files))
    hashes = []
    for file in files:
        md5_string = md5_file(file)
        pair = tuple([md5_string, Path(file).name])
        context.log.info(pair)
        hashes.append(pair)

    yield dg.AssetCheckResult(passed=len(hashes) > 0, check_name="files_found")

    yield dg.Output(value=hashes, metadata={"dagster/num_rows": len(hashes)})


@dg.asset(
    check_specs=[
        dg.AssetCheckSpec(
            name="valid_md5",
            description="Validates that md5 strings match the file content",
            asset="md5_validate",
        )
    ]
)
def md5_validate(
    context: dg.AssetExecutionContext,
    fasta_gz: List[Tuple[str, str]],
    fasta_md5: List[Tuple[str, str]],
) -> Iterator[dg.Output[bool]]:
    """Confirm all valid"""
    result = set(fasta_gz) == set(fasta_md5)
    yield dg.AssetCheckResult(passed=result, check_name="valid_md5")
    yield dg.Output(value=result)


@dg.asset(deps=[md5_validate])
def fastqc_runner(context: dg.AssetExecutionContext, docker_client: PipesDockerClient):
    """Docker execution of fastqc tool"""
    result = docker_client.run(
        image="fastqc",
        command=["python", "/scripts/fastqc.py"],
        context=context,
        container_kwargs={
            "auto_remove": False,
            "volumes": {
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "scripts"): {
                    "bind": "/scripts",
                    "mode": "ro",
                },
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "inputs"): {
                    "bind": "/inputs",
                    "mode": "ro",
                },
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs"): {
                    "bind": "/outputs",
                    "mode": "rw",
                },
            },
        },
    )
    return result.get_results()
