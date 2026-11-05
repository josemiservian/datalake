{#
    Use the custom schema as-is instead of dbt's default "<target_schema>_<custom_schema>",
    so models configured with +schema: silver land in iceberg.silver, not iceberg.gold_silver.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
