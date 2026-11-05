"""SNBE pipeline: Bronze -> Silver -> Gold, one DAG for the whole dataset.

Replaces insert_iceberg_silver_snbe, snbe_active_users_cumulated and
snbe_travels_per_bus_daily. Every transformation runs as a dbt model.

The first Silver run after the move to dbt must be a full refresh, run by hand:
    cd /opt/airflow/elt/dbt && dbt run --select silver_snbe --full-refresh
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

DBT_DIR = '/opt/airflow/elt/dbt'


def dbt_run(model: str) -> BashOperator:
    """Build a task that runs a single dbt model.

    Args:
        model: Name of the dbt model to run.

    Returns:
        The BashOperator, with task_id ``dbt_<model>``.
    """
    return BashOperator(
        task_id=f'dbt_{model}',
        bash_command=f'cd {DBT_DIR} && dbt run --select {model}',
    )


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'snbe_pipeline',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=['snbe'],
) as dag:

    silver = dbt_run('silver_snbe')

    active_users_daily = dbt_run('snbe_active_users_daily')
    active_users_cumulated = dbt_run('snbe_active_users_cumulated')

    # Kept from the old snbe_travels_per_bus_daily DAG, unchanged. The model's
    # `properties` are written as Python lists / unquoted strings, which most likely
    # do not render as valid Trino DDL, so the table is created here and dbt appends.
    create_travels_table = SQLExecuteQueryOperator(
        task_id='create_snbe_travels_per_bus_daily',
        conn_id='trino',
        sql="""
            CREATE TABLE IF NOT EXISTS iceberg.gold.snbe_travels_per_bus_daily (
                id_transporte varchar,
                id_ruta varchar,
                tipo_transporte integer,
                latitude double,
                longitude double,
                hora_viaje timestamp(6),
                fecha_viaje date,
                total_recaudado double,
                cantidad_tarjetas bigint,
                cantidad_viajes bigint,
                loaded_timestamp timestamp(6)
            )
            WITH (
                format = 'PARQUET',
                partitioning = ARRAY['fecha_viaje'],
                sorted_by = ARRAY['hora_viaje'],
                location = 's3a://gold/snbe_travels_per_bus_daily/'
            )
        """,
        autocommit=True,
    )
    travels_per_bus_daily = dbt_run('snbe_travels_per_bus_daily')

    silver >> active_users_daily >> active_users_cumulated
    silver >> create_travels_table >> travels_per_bus_daily
