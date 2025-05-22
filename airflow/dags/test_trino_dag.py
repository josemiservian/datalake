from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from airflow.providers.common.sql.hooks.sql import DbApiHook
from trino.dbapi import connect

from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

class TrinoHook(DbApiHook):
    conn_name_attr = 'trino_conn_id'
    
    def get_conn(self):
        conn = self.get_connection(self.trino_conn_id)
        return connect(
            host=conn.host,
            port=conn.port or 8080, 
            user='trino',
            http_scheme='http',
            auth=None
        )

# Define the SQL query to return a value
query = """select distinct "$path" as filename from minio.bronze.snbe order by 1 """
query = "select version()"
             
# Define the Python function to get sql query
def get_sql_from_xcom(**kwargs):
    ti = kwargs['ti']
    sql_query = ti.xcom_pull(task_ids='sql_test')
    if sql_query:
        return sql_query[0][0]
    else:
        return None
    

# Define the DAG
dag = DAG(
    dag_id='test_trino_dag',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
)

# start = PythonOperator(
#     task_id="start",
#     python_callable = lambda: print("Job started"),
#     dag=dag
# )

# end = PythonOperator(
#     task_id="end",
#     python_callable = lambda: print("Job ended"),
#     dag=dag
# )

sql_test = SQLExecuteQueryOperator(
    task_id='sql_test',
    sql=query,
    conn_id='trino',
    hook_params={
        'auth': False
    },
    dag=dag
)

# sql_test = TrinoOperator(
#     task_id='sql_test',
#     sql=query,
#     trino_conn_id='trino',
#     dag=dag,
# )

get_sql_from_xcom_task = PythonOperator(
    task_id='get_sql_from_xcom_task',
    python_callable=get_sql_from_xcom,
    provide_context=True,
    dag=dag
)

# Dependencies
sql_test >> get_sql_from_xcom_task
