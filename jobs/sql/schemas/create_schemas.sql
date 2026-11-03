CREATE SCHEMA IF NOT EXISTS minio.bronze
WITH (location = 's3a://bronze/');

CREATE SCHEMA IF NOT EXISTS minio.banking
WITH (location = 's3a://bronze/banking/');

CREATE SCHEMA IF NOT EXISTS minio.metadata
WITH (location = 's3a://bronze/metadata/');

CREATE SCHEMA IF NOT EXISTS iceberg.silver
WITH (location = 's3a://silver/');

CREATE SCHEMA IF NOT EXISTS iceberg.gold
WITH (location = 's3a://gold/');

CREATE SCHEMA IF NOT EXISTS minio.tsje
WITH (location = 's3a://bronze/tsje/');

CREATE SCHEMA IF NOT EXISTS minio.ips
WITH (location = 's3a://bronze/ips/');