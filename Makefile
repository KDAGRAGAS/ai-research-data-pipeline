.PHONY: setup ingest transform test run metrics clean

setup:
	python -m pip install -r requirements.txt
	python -m pip install -e .

ingest:
	python -m ai_research_pipeline ingest

transform:
	dbt build --project-dir dbt --profiles-dir dbt_profiles

test:
	pytest
	dbt test --project-dir dbt --profiles-dir dbt_profiles

run:
	python -m ai_research_pipeline run

metrics:
	python -m ai_research_pipeline metrics

clean:
	dbt clean --project-dir dbt --profiles-dir dbt_profiles
