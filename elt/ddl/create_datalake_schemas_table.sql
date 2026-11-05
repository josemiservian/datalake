CREATE TABLE IF NOT EXISTS minio.metadata.datalake_schemas (
  source_type          varchar(20),
  source_name          varchar(100),
  source_domain        varchar(100),
  destination_catalog  varchar(50),
  destination_schema   varchar(50),
  destination_layer    varchar(20),
  destination_domain   varchar(100),
  destination_source   varchar(100),
  destination_format   varchar(20),
  schema_json          varchar(65535),
  table_count          integer,
  column_count         integer,
  metadata_version     integer,
  exported_at          timestamp(3)
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/metadata/datalake_schemas'
);
