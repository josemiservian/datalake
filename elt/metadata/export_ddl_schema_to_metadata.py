import argparse
import base64
import json
import os
from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone

import duckdb
from dotenv import load_dotenv

# Repo root, derived from this file so the script runs from any clone.
BASE = str(Path(__file__).resolve().parents[2])
load_dotenv(os.path.join(BASE, ".env"))

TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.IGNORECASE,
)
TABLE_COMMENT_RE = re.compile(r"\)\s*COMMENT\s+'((?:''|[^'])*)'", re.IGNORECASE | re.DOTALL)
WITH_RE = re.compile(r"WITH\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
LOCATION_RE = re.compile(r"external_location\s*=\s*'([^']+)'", re.IGNORECASE)
FORMAT_RE = re.compile(r"format\s*=\s*'([^']+)'", re.IGNORECASE)


def sql_lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def normalize_type(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    value = re.sub(r"\s*,\s*", ",", value)
    return value.lower()


def trino_query(sql: str, catalog: str, schema: str) -> list[list]:
    host = os.environ.get("TRINO_HOST", "localhost")
    port = os.environ.get("TRINO_PORT", "8080")
    user = os.environ.get("TRINO_USER", "trino-mcp")
    password = os.environ.get("TRINO_PASSWORD")

    headers = {
        "Content-Type": "text/plain",
        "X-Trino-User": user,
        "X-Trino-Catalog": catalog,
        "X-Trino-Schema": schema,
    }
    if password:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    request = urllib.request.Request(
        f"http://{host}:{port}/v1/statement",
        data=sql.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)

    rows: list[list] = []
    while True:
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        rows.extend(payload.get("data") or [])
        next_uri = payload.get("nextUri")
        if not next_uri:
            return rows
        next_request = urllib.request.Request(next_uri, headers=headers)
        with urllib.request.urlopen(next_request) as response:
            payload = json.load(response)


def apply_live_comments(parsed: dict) -> None:
    schema = parsed["schema"]
    table = parsed["table"]
    catalog = parsed["catalog"]

    table_rows = trino_query(
        "SELECT DISTINCT comment FROM system.metadata.table_comments "
        f"WHERE catalog_name = '{catalog}' AND schema_name = '{schema}' "
        f"AND table_name = '{table}' AND comment IS NOT NULL",
        catalog,
        schema,
    )
    if table_rows:
        parsed["table_comment"] = table_rows[0][0]

    column_rows = trino_query(
        "SELECT column_name, comment FROM information_schema.columns "
        f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
        "ORDER BY ordinal_position",
        catalog,
        schema,
    )
    live_comments = {name: comment for name, comment in column_rows}
    for column in parsed["columns"]:
        comment = live_comments.get(column["column_name"])
        if comment is not None:
            column["column_comment"] = comment


def parse_ddl(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    match = TABLE_RE.search(text)
    if not match:
        raise ValueError(f"cannot find CREATE TABLE in {path}")
    catalog, schema, table = match.groups()

    end_match = re.search(r"\n\)\s*(?=COMMENT|WITH|;)", text[match.end() :], re.IGNORECASE)
    if not end_match:
        raise ValueError(f"cannot find end of column list in {path}")

    body_start = match.end()
    body_end = body_start + end_match.start()
    body = text[body_start:body_end]
    tail = text[body_end:]

    table_comment = None
    comment_match = TABLE_COMMENT_RE.search(tail)
    if comment_match:
        table_comment = comment_match.group(1).replace("''", "'")

    with_match = WITH_RE.search(tail)
    if not with_match:
        raise ValueError(f"cannot find WITH options in {path}")
    with_body = with_match.group(1)

    location_match = LOCATION_RE.search(with_body)
    format_match = FORMAT_RE.search(with_body)
    if not location_match or not format_match:
        raise ValueError(f"cannot find external_location/format in {path}")

    location = location_match.group(1).replace("s3a://", "s3://")
    destination_format = format_match.group(1).lower()

    columns = []
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue

        parts = re.split(r"\s+COMMENT\s+", line, maxsplit=1)
        name_and_type = parts[0].strip()
        name, data_type = name_and_type.split(None, 1)

        comment = None
        if len(parts) == 2:
            comment = parts[1].strip()
            if comment.startswith("'") and comment.endswith("'"):
                comment = comment[1:-1].replace("''", "'")

        columns.append(
            {
                "ordinal_position": len(columns) + 1,
                "column_name": name,
                "source_data_type": None,
                "source_udt_name": None,
                "destination_data_type": normalize_type(data_type),
                "is_nullable": True,
                "column_default": None,
                "is_primary_key": False,
                "foreign_key_reference": None,
                "column_comment": comment,
            }
        )

    if not columns:
        raise ValueError(f"no columns found in {path}")

    return {
        "catalog": catalog,
        "schema": schema,
        "table": table,
        "table_comment": table_comment,
        "location": location,
        "format": destination_format,
        "columns": columns,
    }


def build_row(args: argparse.Namespace, parsed: dict) -> dict:
    schema = parsed["schema"]
    table = parsed["table"]
    domain = args.domain or schema
    source = args.source or schema

    schema_json = json.dumps(
        {
            "source_schema": schema,
            "tables": [
                {
                    "source_schema": schema,
                    "source_table": table,
                    "source_table_comment": parsed["table_comment"],
                    "destination_table": table,
                    "destination_location": parsed["location"],
                    "columns": parsed["columns"],
                }
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return {
        "source_type": args.source_type,
        "source_name": source,
        "source_domain": domain,
        "destination_catalog": parsed["catalog"],
        "destination_schema": schema,
        "destination_layer": args.layer,
        "destination_domain": domain,
        "destination_source": source,
        "destination_format": parsed["format"],
        "schema_json": schema_json,
        "table_count": 1,
        "column_count": len(parsed["columns"]),
        "metadata_version": args.metadata_version,
        "exported_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }


def write_row(row: dict, target: str) -> None:
    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_endpoint={sql_lit(endpoint)}")
    con.execute("SET s3_use_ssl=false")
    con.execute("SET s3_url_style='path'")
    con.execute("SET s3_region='us-east-1'")
    con.execute(f"SET s3_access_key_id={sql_lit(os.environ['MINIO_ACCESS_KEY'])}")
    con.execute(f"SET s3_secret_access_key={sql_lit(os.environ['MINIO_SECRET_KEY'])}")

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
            row["source_type"],
            row["source_name"],
            row["source_domain"],
            row["destination_catalog"],
            row["destination_schema"],
            row["destination_layer"],
            row["destination_domain"],
            row["destination_source"],
            row["destination_format"],
            row["schema_json"],
            row["table_count"],
            row["column_count"],
            row["metadata_version"],
            row["exported_at"],
        ],
    )
    con.execute(
        f"COPY metadata_row TO {sql_lit(target)} (FORMAT PARQUET, COMPRESSION SNAPPY)"
    )
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a Trino DDL table definition to the datalake metadata table."
    )
    parser.add_argument("--ddl", required=True, help="Path to the CREATE TABLE .sql file.")
    parser.add_argument("--domain", help="Metadata domain. Defaults to the DDL schema.")
    parser.add_argument("--source", help="Metadata source. Defaults to the DDL schema.")
    parser.add_argument("--source-type", default="parquet", help="Origin system type.")
    parser.add_argument("--layer", default="bronze", help="Medallion layer.")
    parser.add_argument("--metadata-version", type=int, default=1)
    parser.add_argument(
        "--target",
        help="Destination parquet path. Defaults to s3://bronze/metadata/datalake_schemas/<schema>.parquet.",
    )
    parser.add_argument(
        "--live-comments",
        action="store_true",
        help="Override DDL comments with the live Trino table/column comments.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated row without writing to MinIO.",
    )
    args = parser.parse_args()

    parsed = parse_ddl(args.ddl)
    if args.live_comments:
        apply_live_comments(parsed)
    row = build_row(args, parsed)
    target = args.target or (
        f"s3://bronze/metadata/datalake_schemas/{parsed['schema']}.parquet"
    )

    if args.dry_run:
        print(json.dumps(row, ensure_ascii=False, indent=2, default=str))
        return

    write_row(row, target)
    print(
        f"{parsed['schema']}.{parsed['table']}: "
        f"{row['column_count']} columns -> {target}"
    )


if __name__ == "__main__":
    main()
