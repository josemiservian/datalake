{{
  config(
    materialized='incremental',
    alias='snbe_travels_per_bus_daily',
    properties={
      "format": "PARQUET",
      "partitioning": ["fecha_viaje"],
      "sorted_by": ["hora_viaje"],
      "location": "s3a://gold/snbe_travels_per_bus_daily/",
      "iceberg.catalog": "iceberg"
    },
    incremental_strategy='append'
  )
}}

{% set process_all = var('process_all', false) %}
{% set reprocess_date = var('reprocess_date', false) %}
{% set custom_range = var('custom_range', false) %}

{% if custom_range %}
  {% set start_date = var('start_date') %}
  {% set end_date = var('end_date') %} 
{% elif reprocess_date %}
  {% set start_date = reprocess_date %}
  {% set end_date = reprocess_date %}
{% elif process_all %}
  {% set start_date = var("initial_load_date", "2022-01-01") %}
  {% set end_date = var('end_date', modules.datetime.datetime.now().strftime("%Y-%m-%d")) %}
{% else %}
{# Incremental #}
  {% set incremental_query %}
    SELECT 
      COALESCE(
        DATE_ADD('day', 1, MAX(fecha_viaje)),
        DATE '{{ var("initial_load_date", "2022-01-01") }}'
      ) AS start_date
    FROM {{ this }}
  {% endset %}

  {% set results = run_query(incremental_query) %}
  {% if execute %}
    {% set start_date = results.columns[0][0].strftime("%Y-%m-%d") %}
  {% else %}
    {% set start_date = var("initial_load_date", "2022-01-01") %}
  {% endif %}
  {% set end_date = (modules.datetime.datetime.strptime(start_date, "%Y-%m-%d") + modules.datetime.timedelta(days=30)).strftime("%Y-%m-%d") %}
  {% set current_date = modules.datetime.datetime.now().strftime("%Y-%m-%d") %}
  {% set end_date = [end_date, current_date]|min %}
{% endif %}

WITH daily_travels AS (
  SELECT
      idsam AS id_transporte,
      idrutaestacion AS id_ruta,    
      tipotransporte AS tipo_transporte,
      latitude,
      longitude,
      date_trunc('hour', fechahoraevento) AS hora_viaje,
      fecha_evento AS fecha_viaje,
      SUM(montoevento) AS total_recaudado,
      COUNT(DISTINCT serialtarjeta) AS cantidad_tarjetas,
      COUNT(*) AS cantidad_viajes,
      CURRENT_TIMESTAMP as loaded_timestamp
  FROM {{ source('silver', 'snbe') }}
  WHERE fecha_evento BETWEEN DATE '{{ start_date }}' AND DATE '{{ end_date }}'
  AND tipoevento = 4
    -- {% if is_incremental() and not process_all and not reprocess_date %}
    --   AND fecha_evento >= DATE '{{ start_date }}'
    -- {% endif %}
  GROUP BY 
      idsam,
      idrutaestacion,    
      tipotransporte,
      latitude,
      longitude,
      date_trunc('hour', fechahoraevento),
      fecha_evento
)

SELECT * FROM daily_travels
