# rna-sequence
Dagster enabled pipeline to run rna-sequence bioinformatics

Commands to remove legacy docker containers:
```bash
docker ps -aq -f status=exited -f ancestor=image_name | xargs -r docker rm
```