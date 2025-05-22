from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from pathlib import Path
import json

sql_dir = '/opt/airflow/jobs/sql/snbe'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def read_sql_file(file_name):
    sql_path = os.path.join(sql_dir, file_name)
    with open(sql_path, 'r') as file:
        return file.read()

def process_file_with_sql_template(**context):
    ti = context['ti']
    file_paths = ti.xcom_pull(task_ids='get_distinct_paths')
    
    # Convertimos los resultados a una lista de strings
    paths = [str(record[0]) for record in file_paths]
    
    # Devolvemos un objeto serializable (lista de strings)
    return paths

def create_insert_tasks(**context):
    ti = context['ti']
    paths = ti.xcom_pull(task_ids='process_files')
    
    # Creamos y devolvemos una lista de diccionarios con la información necesaria
    tasks_info = []
    for path in paths:
        sql_template = read_sql_file('iceberg_silver_insert_from_path.sql')
        formatted_sql = sql_template.replace("{{ path }}", path)
        
        tasks_info.append({
            'task_id': f'insert_file_{hash(path)}',
            'sql': formatted_sql
        })
    
    return tasks_info

def execute_insert_tasks(**context):
    ti = context['ti']
    tasks_info = ti.xcom_pull(task_ids='create_insert_tasks')
    
    for task_info in tasks_info:
        SQLExecuteQueryOperator(
            task_id=task_info['task_id'],
            conn_id='trino',
            sql=task_info['sql'],
            autocommit=True,
            dag=context['dag']
        ).execute(context)

with DAG(
    'insert_iceberg_silver_snbe',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    create_table = SQLExecuteQueryOperator(
        task_id='create_iceberg_table',
        conn_id='trino',
        sql=read_sql_file('create_table_iceberg_silver.sql'),
        autocommit=True,
    )

    get_distinct_paths = SQLExecuteQueryOperator(
        task_id='get_distinct_paths',
        conn_id='trino',
        sql=read_sql_file('get_distinct_paths.sql'),
        autocommit=True,
    )

    process_files = PythonOperator(
        task_id='process_files',
        python_callable=process_file_with_sql_template,
        provide_context=True,
    )

    create_insert_tasks_op = PythonOperator(
        task_id='create_insert_tasks',
        python_callable=create_insert_tasks,
        provide_context=True,
    )

    execute_insert_tasks_op = PythonOperator(
        task_id='execute_insert_tasks',
        python_callable=execute_insert_tasks,
        provide_context=True,
    )

    create_table >> get_distinct_paths >> process_files >> create_insert_tasks_op >> execute_insert_tasks_op