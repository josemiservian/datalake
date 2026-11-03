import os
import subprocess

import duckdb
from dotenv import load_dotenv

BASE = "/home/josemi/repositories/datalake"
load_dotenv(os.path.join(BASE, ".env"))


def sql_lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def default_gateway() -> str:
    for cmd in (
        "ip route show default dev eth0 | awk 'NR==1 {print $3}'",
        "ip route show default | awk 'NR==1 {print $3}'",
    ):
        try:
            out = subprocess.check_output(cmd, shell=True, text=True).strip()
            if out:
                return out
        except subprocess.CalledProcessError:
            pass
    raise RuntimeError("cannot determine host gateway; set ITAHU_HOST")


PG_HOST = os.environ.get("ITAHU_HOST") or default_gateway()
PG_USER = os.environ.get("ITAHU_USER", "mcp_reader")
PG_PASSWORD = os.environ.get("ITAHU_PASSWORD", "mcp_reader")
PG_DSN = (
    f"host={PG_HOST} port=5432 dbname=itahu "
    f"user={PG_USER} password={PG_PASSWORD}"
)

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
DOMAIN = "banking"

TABLES = [
    "clientes",
    "cuentas",
    "movimiento",
    "tasas_interes",
    "tipos_cuentas",
    "tipos_movimiento",
]

con = duckdb.connect()
con.execute("INSTALL postgres; LOAD postgres;")
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"ATTACH {sql_lit(PG_DSN)} AS pg (TYPE POSTGRES, READ_ONLY);")

con.execute(f"SET s3_endpoint={sql_lit(MINIO_ENDPOINT)}")
con.execute("SET s3_use_ssl=false")
con.execute("SET s3_url_style='path'")
con.execute("SET s3_region='us-east-1'")
con.execute(f"SET s3_access_key_id={sql_lit(os.environ['MINIO_ACCESS_KEY'])}")
con.execute(f"SET s3_secret_access_key={sql_lit(os.environ['MINIO_SECRET_KEY'])}")

for table in TABLES:
    dst = f"s3://bronze/{DOMAIN}/{table}/data.parquet"
    rows = con.execute(f"SELECT count(*) FROM pg.public.{table}").fetchone()[0]
    con.execute(
        f"COPY (SELECT * FROM pg.public.{table}) TO {sql_lit(dst)} "
        "(FORMAT PARQUET, COMPRESSION SNAPPY)"
    )
    print(f"{table}: {rows} rows -> {dst}")

con.execute("DETACH pg")
con.close()
