from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

DBT_DIR = '/opt/airflow/elt/dbt'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'insert_iceberg_silver_snbe',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    # Incremental model: loads only the Bronze files not yet present in Silver.
    # First run after the migration: trigger with --full-refresh (see the model header).
    silver_snbe = BashOperator(
        task_id='dbt_silver_snbe',
        bash_command=f'cd {DBT_DIR} && dbt run --select silver_snbe',
    )
