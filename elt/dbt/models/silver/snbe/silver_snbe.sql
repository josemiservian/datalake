{#
    Replaces the old per-file INSERT loop (airflow/dags/snbe/silver_snbe.py + jobs/sql/snbe/).
    Each run loads only the Bronze files whose path is not yet in Silver (_source_path).

    The pre-existing iceberg.silver.snbe has no _source_path column, so the first run
    after this change must rebuild it:  dbt run --select silver_snbe --full-refresh
#}
{{
  config(
    materialized='incremental',
    alias='snbe',
    incremental_strategy='append',
    properties={
      "format": "'PARQUET'",
      "partitioning": "ARRAY['fecha_evento']",
      "sorted_by": "ARRAY['fechahoraevento']",
      "location": "'s3a://silver/snbe/'"
    }
  )
}}

with bronze as (
    select
        *,
        "$path" as _source_path
    from {{ source('bronze', 'snbe') }}
    {% if is_incremental() %}
    where "$path" not in (
        select _source_path
        from {{ this }}
        where _source_path is not null
    )
    {% endif %}
)

select
    serialtarjeta,
    idsam,
    cast(date_parse(fechahoraevento, '%Y/%m/%d %H:%i:%s.%f') as timestamp(6)) as fechahoraevento,
    producto,
    cast(montoevento as integer) as montoevento,
    cast(consecutivoevento as integer) as consecutivoevento,
    cast(identidad as integer) as identidad,
    cast(tipoevento as integer) as tipoevento,
    cast(nullif(trim(latitude), '') as double) as latitude,
    cast(nullif(trim(longitude), '') as double) as longitude,
    idrutaestacion,
    cast(tipotransporte as integer) as tipotransporte,
    cast(date_parse(substr(fechahoraevento, 1, 19), '%Y/%m/%d %H:%i:%S') as date) as fecha_evento,
    _source_path
from bronze
