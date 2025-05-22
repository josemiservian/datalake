from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 6),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'snbe_travels_per_bus_daily',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:
    
    start = PythonOperator(
        task_id="start",
        python_callable = lambda: print("Jobs started"),
        dag=dag
    )

    create_table = SQLExecuteQueryOperator(
        task_id='create_table',
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

    dbt = BashOperator(
        task_id='dbt_incremental_job',
        bash_command='cd /opt/airflow/jobs/dbt/transformations && dbt run --models gold.snbe_travels_per_bus_daily',
    )

    end = PythonOperator(
        task_id="end",
        python_callable = lambda: print("Jobs completed successfully"),
        dag=dag
    )

    start >> create_table >> dbt >> end


