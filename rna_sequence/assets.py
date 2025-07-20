import hashlib
import os
from glob import glob
from operator import attrgetter as at
from operator import methodcaller as mc
from pathlib import Path
from typing import Iterator, List, Tuple

from dagster_docker import PipesDockerClient
from toolz import compose, first, last

import dagster as dg


class RnaSequenceConfig(dg.Config):
    input_pattern: str = "MD5.txt"
    input_folder: str = "/inputs"

    output_pattern: str = "*.gz"
    output_folder: str = "/outputs"

    umi_bc_pattern: str = "NNNNCCCCNNN"
    umi_parallel: int = 24

    fastp_parallel: int = 24

@dg.asset(
    check_specs=[
        dg.AssetCheckSpec(
            name="files_found",
            description="Validates existance of md5 files",
            asset="fasta_md5",
            blocking=True,
        )
    ],
    kinds={"python"}
)
def fasta_md5(
    context: dg.AssetExecutionContext, config: RnaSequenceConfig
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
            blocking=True,
        )
    ],
    kinds={"python"}
)
def fasta_gz(
    context: dg.AssetExecutionContext, config: RnaSequenceConfig
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
    ins={
        "fasta_gz": dg.AssetIn(key="fasta_gz"),
        "fasta_md5": dg.AssetIn(key="fasta_md5"),
    },
    check_specs=[
        dg.AssetCheckSpec(
            name="valid_md5",
            description="Validates that md5 strings match the file content",
            asset="md5_validate",
            blocking=True,
        )
    ],
    kinds={"python"},
)
def md5_validate(
    context: dg.AssetExecutionContext,
    fasta_gz: List[Tuple[str, str]],
    fasta_md5: List[Tuple[str, str]],
) -> Iterator[dg.Output[Tuple[bool, List[str]]]]:
    """Confirm all valid"""
    inventory = set(fasta_gz)
    result = inventory == set(fasta_md5)
    yield dg.AssetCheckResult(passed=result, check_name="valid_md5")

    _names = list(map(last, inventory))
    yield dg.Output(value=tuple([result, _names]))


@dg.asset(
    ins={"md5_validate": dg.AssetIn(key="md5_validate")},
    check_specs=[
        dg.AssetCheckSpec(
            name="full_sequence",
            description="Reports created for all sequences",
            asset="fastqc_runner",
            blocking=True,
        )
    ],
    kinds={"docker"},
)
def fastqc_runner(
    context: dg.AssetExecutionContext,
    docker_client: PipesDockerClient,
    md5_validate: Tuple[bool, List[str]],
) -> Iterator[dg.Output[str]]:
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

    files_io = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs"))
    _, files_spec = md5_validate

    _stems = compose(first, mc("split", "-"), at("stem"), Path)
    _f_stems = list(map(_stems, files_spec))
    _f_outs = list(map(_stems, files_io))
    complete = set(_f_stems).issubset(set(_f_outs))

    yield dg.AssetCheckResult(passed=complete, check_name="full_sequence")

    yield dg.Output(value=str(result.get_results()))


@dg.asset(
    deps=[fastqc_runner],
    check_specs=[
        dg.AssetCheckSpec(
            name="adapter_trim",
            description="Trimming all sequences",
            asset="umitools_runner",
            blocking=True,
        )
    ],
    kinds={"docker"},
)
def umitools_runner(
    context: dg.AssetExecutionContext,
    config: RnaSequenceConfig,
    docker_client: PipesDockerClient,    
) -> Iterator[dg.Output[str]]:
    """Docker execution of umi_tool tool"""
    result = docker_client.run(
        image="umitools",
        command=["python", "/scripts/umitools.py"],
        context=context,
        extras={
            "bc_pattern": config.umi_bc_pattern,
            "parallel_threads": config.umi_parallel
        },
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
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs2"): {
                    "bind": "/outputs",
                    "mode": "rw",
                },
            },
        },
    )

    files_in = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "inputs"))
    files_out = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs2"))    

    _stems = compose(first, mc("split", "-"), at("stem"), Path)
    _f_ins = list(map(_stems, files_in))
    _f_outs = list(map(_stems, files_out))
    complete = set(_f_ins).issubset(set(_f_outs))

    yield dg.AssetCheckResult(passed=complete, check_name="adapter_trim")

    yield dg.Output(value=str(result.get_results()))

@dg.asset(
    deps=[umitools_runner],
    check_specs=[
        dg.AssetCheckSpec(
            name="nucleotide_trim",
            description="Trimming fastp nucleaotide check",
            asset="fastp_runner",
            blocking=True,
        )
    ],
    kinds={"docker"},
)
def fastp_runner(
    context: dg.AssetExecutionContext,
    config: RnaSequenceConfig,
    docker_client: PipesDockerClient,    
) -> Iterator[dg.Output[str]]:
    """Docker execution of fastp tool"""
    result = docker_client.run(
        image="fastp",
        command=["python", "/scripts/fastp.py"],
        context=context,
        extras={            
            "parallel_threads": config.fastp_parallel
        },
        container_kwargs={
            "auto_remove": False,
            "volumes": {
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "scripts"): {
                    "bind": "/scripts",
                    "mode": "ro",
                },
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs2"): {
                    "bind": "/inputs",
                    "mode": "ro",
                },
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs3"): {
                    "bind": "/outputs",
                    "mode": "rw",
                },
            },
        },
    )

    # files_in = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "inputs"))
    # files_out = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs2"))    

    # _stems = compose(first, mc("split", "-"), at("stem"), Path)
    # _f_ins = list(map(_stems, files_in))
    # _f_outs = list(map(_stems, files_out))
    # complete = set(_f_ins).issubset(set(_f_outs))

    yield dg.AssetCheckResult(passed=True, check_name="nucleotide_trim")

    yield dg.Output(value=str(result.get_results()))


@dg.asset(
    deps=[fastp_runner],
    check_specs=[
        dg.AssetCheckSpec(
            name="full_sequence",
            description="Reports created for all sequences",
            asset="fastqc_post",
            blocking=True,
        )
    ],
    kinds={"docker"},
)
def fastqc_post(
    context: dg.AssetExecutionContext,
    docker_client: PipesDockerClient,    
) -> Iterator[dg.Output[str]]:
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
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs3"): {
                    "bind": "/inputs",
                    "mode": "ro",
                },
                str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs4"): {
                    "bind": "/outputs",
                    "mode": "rw",
                },
            },
        },
    )

    # files_io = os.listdir(str(Path(os.getenv("RNA_SEQUENCE_HOME")) / "outputs"))
    # _, files_spec = md5_validate

    # _stems = compose(first, mc("split", "-"), at("stem"), Path)
    # _f_stems = list(map(_stems, files_spec))
    # _f_outs = list(map(_stems, files_io))
    # complete = set(_f_stems).issubset(set(_f_outs))

    yield dg.AssetCheckResult(passed=True, check_name="full_sequence")

    yield dg.Output(value=str(result.get_results()))