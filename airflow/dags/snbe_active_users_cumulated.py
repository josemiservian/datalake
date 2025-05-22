from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 16),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'snbe_active_users_cumulated',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:
    
    start = PythonOperator(
        task_id="start",
        python_callable = lambda: print("Jobs started"),
        dag=dag
    )

    daily_task = BashOperator(
        task_id='daily_incremental_job',
        bash_command='cd /opt/airflow/jobs/dbt/transformations && dbt run --models gold.snbe_active_users_daily',
    )

    cumulative_task = BashOperator(
        task_id='cumulative_incremental_job',
        bash_command='cd /opt/airflow/jobs/dbt/transformations && dbt run --models gold.snbe_active_users_cumulated',
    )
    
    end = PythonOperator(
        task_id="end",
        python_callable = lambda: print("Jobs completed successfully"),
        dag=dag
    )

    start >> daily_task >> cumulative_task >> end


