clean: # Remove workspace files
	@find . -name "__pycache__" -exec rm -rf {} +
	@rm -rf ./.pytest_cache
	@rm -rf ./htmlcov
	@rm -rf rna_sequence.egg-info
	@rm -rf dist/
	@rm -rf build/
	@rm -rf __blobstorage__
	@rm -rf __marimo__
	@rm -rf .ipynb_checkpoints
	@rm -rf .mypy_cache
	@rm -rf spark-warehouse/
	@rm -rf .ruff_cache
	@rm -rf report.xml
	@rm -rf .coverage
	@echo "✨ done"

format: # Format code
	@uv run black rna_sequence

cov: # Run test and coverage
	uv run coverage run -m pytest -v test/unit
	uv run coverage xml -o temp/coverage.xml

ruff: # Lint code
	@uv run ruff check rna_sequence
	@echo "✨ done"

report: # Launches the coverage report
	@coverage html
	@python -m http.server --directory htmlcov

pack: # Package wheel
	@python -m build

type: # Verify static types
	@mypy --install-types --non-interactive rna_sequence
	@echo "✨ done"

unit: # Run unit test
	@uv run pytest test/unit

renew: # Clean up home
	@rm -rf dagster
	@mkdir -p dagster
	@cp conf/dagster.yaml dagster/
	@echo "✨ done"

launch: # Start dagster
	export DAGSTER_HOME=$$PWD/dagster
	uv run dagster dev -m rna_sequence

commit: # Run pre-commit
	@uv run pre-commit run --all-files
