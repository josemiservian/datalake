import json
import os
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone

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

SOURCE_TYPE = "postgresql"
SOURCE_NAME = "itahu"
SOURCE_DOMAIN = "banking"
DESTINATION_CATALOG = "minio"
DESTINATION_SCHEMA = "banking"
DESTINATION_LAYER = "bronze"
DESTINATION_DOMAIN = "banking"
DESTINATION_SOURCE = "itahu"
DESTINATION_FORMAT = "parquet"
METADATA_VERSION = 1

TARGET = "s3://bronze/metadata/datalake_schemas/postgres_itahu.parquet"
SQL_PATH = os.path.join(BASE, "jobs/sql/schemas/get_itahu_schema.sql")

with open(SQL_PATH, "r", encoding="utf-8") as f:
    schema_sql = f.read()

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

rows = con.execute(
    "SELECT * FROM postgres_query(?, ?)", ["pg", schema_sql]
).fetchall()
column_names = [desc[0] for desc in con.description]
records = [dict(zip(column_names, row)) for row in rows]

tables = OrderedDict()
for rec in records:
    key = (rec["source_schema"], rec["source_table"])
    table = tables.setdefault(
        key,
        {
            "source_schema": rec["source_schema"],
            "source_table": rec["source_table"],
            "source_table_comment": rec["source_table_comment"],
            "destination_table": rec["source_table"],
            "destination_location": f"s3://bronze/{DESTINATION_SCHEMA}/{rec['source_table']}",
            "columns": [],
        },
    )
    table["columns"].append(
        {
            "ordinal_position": rec["ordinal_position"],
            "column_name": rec["column_name"],
            "source_data_type": rec["source_data_type"],
            "source_udt_name": rec["source_udt_name"],
            "destination_data_type": rec["destination_data_type"],
            "is_nullable": rec["is_nullable"],
            "column_default": rec["column_default"],
            "is_primary_key": rec["is_primary_key"],
            "foreign_key_reference": rec["foreign_key_reference"],
            "column_comment": rec["column_comment"],
        }
    )

source_schemas = sorted({rec["source_schema"] for rec in records})
schema_payload = {
    "source_schema": source_schemas[0] if len(source_schemas) == 1 else source_schemas,
    "tables": list(tables.values()),
}
schema_json = json.dumps(schema_payload, ensure_ascii=False, separators=(",", ":"))

con.execute(
    """
    CREATE OR REPLACE TABLE metadata_row (
      source_type VARCHAR,
      source_name VARCHAR,
      source_domain VARCHAR,
      destination_catalog VARCHAR,
      destination_schema VARCHAR,
      destination_layer VARCHAR,
      destination_domain VARCHAR,
      destination_source VARCHAR,
      destination_format VARCHAR,
      schema_json VARCHAR,
      table_count INTEGER,
      column_count INTEGER,
      metadata_version INTEGER,
      exported_at TIMESTAMP
    )
    """
)
con.execute(
    "INSERT INTO metadata_row VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [
        SOURCE_TYPE,
        SOURCE_NAME,
        SOURCE_DOMAIN,
        DESTINATION_CATALOG,
        DESTINATION_SCHEMA,
        DESTINATION_LAYER,
        DESTINATION_DOMAIN,
        DESTINATION_SOURCE,
        DESTINATION_FORMAT,
        schema_json,
        len(tables),
        len(records),
        METADATA_VERSION,
        datetime.now(timezone.utc).replace(tzinfo=None),
    ],
)
con.execute(
    f"COPY metadata_row TO {sql_lit(TARGET)} (FORMAT PARQUET, COMPRESSION SNAPPY)"
)

print(f"{len(records)} columns across {len(tables)} tables -> {TARGET}")
con.execute("DETACH pg")
con.close()
