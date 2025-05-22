{{
  config(
    materialized='incremental',
    alias='snbe_active_users_cumulated',
    properties={
      "format": "PARQUET",
      "partitioning": ["snapshot_date"],
      "location": "s3a://gold/snbe_active_users_cumulated",
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

-- insert into iceberg.gold.snbe_active_users_cumulated 
WITH yesterday AS (
    SELECT * 
    FROM {{ this }} sauc   
    WHERE snapshot_date = date_add('day', -1, date'{{ start_date }}')
),

today AS (
    SELECT * 
    FROM {{ source('gold', 'snbe_active_users_daily') }}
    WHERE snapshot_date = date'{{ start_date }}'
),

combined as (
    select
    	coalesce(y.user_id, t.user_id) as user_id
    	, coalesce(
    		IF(CARDINALITY( y.activity_array) < 30,
            	ARRAY[COALESCE(t.is_active_today, 0)] || y.activity_array,
            	ARRAY[COALESCE(t.is_active_today, 0)] || REVERSE(SLICE(REVERSE(y.activity_array),2,29))
         	),  ARRAY[t.is_active_today]
 		) as activity_array
 		, COALESCE(
			IF(CARDINALITY( y.amount_spent_array) < 30,
	            ARRAY[COALESCE(t.amount_spent, 0)] || y.amount_spent_array,
	            ARRAY[COALESCE(t.amount_spent, 0)] || REVERSE(SLICE(REVERSE(y.amount_spent_array),2,29))
	          )
	        , ARRAY[t.amount_spent]
	    ) as amount_spent_array,
        COALESCE(
            IF(CARDINALITY( y.internal_bus_array) < 30,
                ARRAY[COALESCE(t.num_internal_bus, 0)] || y.internal_bus_array,
                ARRAY[COALESCE(t.num_internal_bus, 0)] || REVERSE(SLICE(REVERSE(y.internal_bus_array),2,29))
                )
            , ARRAY[t.num_internal_bus]
        ) as internal_bus_array,
        COALESCE(
            IF(CARDINALITY( y.normal_bus_array) < 30,
                ARRAY[COALESCE(t.num_normal_bus, 0)] || y.normal_bus_array,
                ARRAY[COALESCE(t.num_normal_bus, 0)] || REVERSE(SLICE(REVERSE(y.normal_bus_array),2,29))
            )
            , ARRAY[t.num_normal_bus]
        ) as normal_bus_array,
        COALESCE(
            IF(CARDINALITY( y.ac_bus_array) < 30,
                ARRAY[COALESCE(t.num_ac_bus, 0)] || y.ac_bus_array,
                ARRAY[COALESCE(t.num_ac_bus, 0)] || REVERSE(SLICE(REVERSE(y.ac_bus_array),2,29))
            )
            , ARRAY[t.num_ac_bus]
        ) as ac_bus_array,
        COALESCE(
            IF(CARDINALITY( y.first_travel_array) < 30,
                ARRAY[COALESCE(t.first_travel_hour, 0)] || y.first_travel_array,
                ARRAY[COALESCE(t.first_travel_hour, 0)] || REVERSE(SLICE(REVERSE(y.first_travel_array),2,29))
            )
            , ARRAY[t.first_travel_hour]
        ) as first_travel_array,
        COALESCE(
            IF(CARDINALITY( y.last_travel_array) < 30,
                ARRAY[COALESCE(t.last_travel_hour, 0)] || y.last_travel_array,
                ARRAY[COALESCE(t.last_travel_hour, 0)] || REVERSE(SLICE(REVERSE(y.last_travel_array),2,29))
            )
            , ARRAY[t.last_travel_hour]
        ) as last_travel_array,
        coalesce(t.snapshot_date, date'{{ start_date }}') as snapshot_date
    from yesterday y
    full outer join today t
    on t.user_id = y.user_id
)

SELECT
    user_id,
    activity_array[1] AS is_daily_active,
    CASE WHEN SUM(activity_arr) > 0 THEN 1 ELSE 0 END AS is_monthly_active,
    CASE WHEN SUM(activity_arr_7d) > 0 THEN 1 ELSE 0 END AS is_weekly_active,
    activity_array,
    amount_spent_array,
    internal_bus_array,
    normal_bus_array,
    ac_bus_array,
    first_travel_array,
    last_travel_array,
    SUM(amount_spent_arr_7d) as amount_spent_7d,
    SUM(internal_bus_arr_7d) as num_internal_bus_7d,
    SUM(normal_bus_arr_7d) as num_normal_bus_7d,
    SUM(ac_bus_arr_7d) as num_ac_bus_7d,
    AVG(first_travel_arr_7d) as median_first_travel_hour_7d,
    AVG(last_travel_arr_7d) as median_last_travel_hour_7d,
    SUM(amount_spent_arr) as amount_spent_30d,
    SUM(internal_bus_arr) as num_internal_bus_30d,
    SUM(normal_bus_arr) as num_normal_bus_30d,    
    SUM(ac_bus_arr) as num_ac_bus_30d,
    AVG(first_travel_arr) as median_first_travel_hour_30d,
    AVG(last_travel_arr) as median_last_travel_hour_30d,
    snapshot_date
FROM combined,
unnest(
    activity_array, 
    amount_spent_array,
    internal_bus_array,
    normal_bus_array,
    ac_bus_array,
    first_travel_array,
    last_travel_array,
    SLICE(activity_array, 1, 7),
    SLICE(amount_spent_array, 1, 7),
    SLICE(internal_bus_array, 1, 7),
    SLICE(normal_bus_array, 1, 7),
    SLICE(ac_bus_array, 1, 7),
    SLICE(first_travel_array, 1, 7),
    SLICE(last_travel_array, 1, 7)
) AS t(
    activity_arr, 
    amount_spent_arr,
    internal_bus_arr,
    normal_bus_arr,
    ac_bus_arr,
    first_travel_arr,
    last_travel_arr,
    activity_arr_7d,
    amount_spent_arr_7d,
    internal_bus_arr_7d,
    normal_bus_arr_7d,
    ac_bus_arr_7d,
    first_travel_arr_7d,
    last_travel_arr_7d
)
group by 
	user_id,
    activity_array[1],
	activity_array,
    amount_spent_array,
    internal_bus_array,
    normal_bus_array,
    ac_bus_array,
    first_travel_array,
    last_travel_array,
    snapshot_date