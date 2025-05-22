FROM python:3

RUN apt-get update \
    && apt-get install -y --no-install-recommends

# WORKDIR /home/josemi/datalake/dbt/dbt_project

# # Install the dbt Postgres adapter. This step will also install dbt-core
# RUN pip install --upgrade pip
# RUN pip install dbt-postgres
# RUN pip install dbt-trino

# # Install dbt dependencies (as specified in packages.yml file)
# # Build seeds, models and snapshots (and run tests wherever applicable)
# CMD dbt deps && dbt build --profiles-dir profiles && sleep infinity
