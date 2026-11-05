SELECT
  n.nspname AS source_schema,
  c.relname AS source_table,
  obj_description(c.oid, 'pg_class') AS source_table_comment,
  a.attnum AS ordinal_position,
  a.attname AS column_name,
  format_type(a.atttypid, a.atttypmod) AS source_data_type,
  t.typname AS source_udt_name,
  NOT a.attnotnull AS is_nullable,
  pg_get_expr(d.adbin, d.adrelid) AS column_default,
  COALESCE(pk.is_primary_key, false) AS is_primary_key,
  fk.fk_ref AS foreign_key_reference,
  col_description(c.oid, a.attnum) AS column_comment,
  CASE
    WHEN t.typname = 'int2' THEN 'smallint'
    WHEN t.typname = 'int4' THEN 'integer'
    WHEN t.typname = 'int8' THEN 'bigint'
    WHEN t.typname = 'bool' THEN 'boolean'
    WHEN t.typname = 'date' THEN 'date'
    WHEN t.typname = 'timestamp' THEN 'timestamp(3)'
    WHEN t.typname = 'varchar' THEN 'varchar(' || (a.atttypmod - 4) || ')'
    WHEN t.typname = 'bpchar' THEN 'char(' || (a.atttypmod - 4) || ')'
    WHEN t.typname = 'text' THEN 'varchar'
    WHEN t.typname = 'numeric'
      THEN 'decimal(' || ((a.atttypmod - 4) >> 16) || ',' || ((a.atttypmod - 4) & 65535) || ')'
    ELSE format_type(a.atttypid, a.atttypmod)
  END AS destination_data_type
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
JOIN pg_catalog.pg_attribute a
  ON a.attrelid = c.oid
 AND a.attnum > 0
 AND NOT a.attisdropped
JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
LEFT JOIN pg_catalog.pg_attrdef d
  ON d.adrelid = c.oid
 AND d.adnum = a.attnum
LEFT JOIN LATERAL (
  SELECT true AS is_primary_key
  FROM pg_catalog.pg_constraint con
  WHERE con.conrelid = c.oid
    AND con.contype = 'p'
    AND a.attnum = ANY (con.conkey)
  LIMIT 1
) pk ON true
LEFT JOIN LATERAL (
  SELECT format('%I.%I(%I)', fn.nspname, fc.relname, fa.attname) AS fk_ref
  FROM pg_catalog.pg_constraint con
  JOIN pg_catalog.pg_class fc ON fc.oid = con.confrelid
  JOIN pg_catalog.pg_namespace fn ON fn.oid = fc.relnamespace
  JOIN pg_catalog.pg_attribute fa
    ON fa.attrelid = con.confrelid
   AND fa.attnum = con.confkey[array_position(con.conkey, a.attnum)]
  WHERE con.conrelid = c.oid
    AND con.contype = 'f'
    AND a.attnum = ANY (con.conkey)
  LIMIT 1
) fk ON true
WHERE n.nspname = 'public'
  AND c.relname IN (
    'clientes',
    'cuentas',
    'movimiento',
    'tasas_interes',
    'tipos_cuentas',
    'tipos_movimiento'
  )
  AND c.relkind = 'r'
ORDER BY c.relname, a.attnum
