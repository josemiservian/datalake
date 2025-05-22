{{
  config(
    materialized='incremental',
    alias='snbe_active_users_daily',
    properties={
      "format": "PARQUET",
      "partitioning": ["snapshot_date"],
      "location": "s3a://gold/snbe_active_users_daily",
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
        DATE_ADD('day', 1, MAX(snapshot_date)),
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

select
	serialtarjeta as user_id
	, if(count(serialtarjeta) > 0, 1, 0) as is_active_today
	, count(*) as num_travels
	, sum(montoevento) as amount_spent
	, sum(case tipotransporte when 0 then 1 else 0 end) as num_internal_bus
	, sum(case tipotransporte when 1 then 1 else 0 end) as num_normal_bus
	, sum(case tipotransporte when 3 then 1 else 0 end) as num_ac_bus
	, min(extract(hour from fechahoraevento)) as first_travel_hour
	, max(extract(hour from fechahoraevento)) as last_travel_hour
	, cast('{{ start_date }}' as date) as snapshot_date
from {{ source('silver', 'snbe') }} s 
where s.fecha_evento = date'{{ start_date }}'
and s.tipoevento = 4
group by serialtarjeta