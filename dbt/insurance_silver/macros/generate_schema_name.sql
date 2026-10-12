-- ---------------------------------------------------------------------------
-- generate_schema_name
-- Overrides dbt's default behavior of prefixing custom schemas with the
-- target schema. With this macro, +schema: insurance_bronze stays exactly
-- "insurance_bronze" rather than becoming "insurance_silver_insurance_bronze".
-- ---------------------------------------------------------------------------
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
