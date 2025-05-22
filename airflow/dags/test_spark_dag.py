import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

# import sys
# sys.path.append('/opt/airflow/jobs')

# from test import main

dag = DAG(
    dag_id = "test_spark_dag",
    default_args = {
        "owner": "airflow",
        "start_date": airflow.utils.dates.days_ago(1)
    },
    schedule_interval = None
)

start = PythonOperator(
    task_id="start",
    python_callable = lambda: print("Jobs started"),
    dag=dag
)

python_job = SparkSubmitOperator(
    task_id="python_job",
    conn_id="spark_connection",
    application="/opt/airflow/jobs/test.py",
    verbose=True,
    # conf={
    #     "spark.master": "spark://spark-master:7077",
    #     "spark.submit.deployMode": "client",
    #     "spark.executor.memory": "1g",
    #     "spark.driver.memory": "1g"
    # },
    conf={
        "spark.master": "spark://spark-master:7077",
        "spark.submit.deployMode": "client",
        "spark.network.timeout": "600s",
        "spark.executor.heartbeatInterval": "60s",
        "spark.ui.showConsoleProgress": "false"
    },
    dag=dag
)

# python_job = PythonOperator(
#     task_id="python_job",
#     python_callable=main,
#     dag=dag
# )

end = PythonOperator(
    task_id="end",
    python_callable = lambda: print("Jobs completed successfully"),
    dag=dag
)

start >> python_job >> end