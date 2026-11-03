CREATE TABLE IF NOT EXISTS minio.banking.clientes (
  codigo_cliente decimal(12,0),
  nombres        varchar(120),
  fecha_alta     date,
  fecha_baja     date,
  domicilio      varchar(100),
  ruc            varchar(20)
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/clientes'
);

CREATE TABLE IF NOT EXISTS minio.banking.cuentas (
  anho           smallint,
  numero_cuenta  decimal(12,0),
  codigo_tasa    smallint,
  fecha_apertura timestamp(3),
  codigo_cliente decimal(12,0),
  codigo_tipo    integer,
  codigo_cuenta  integer,
  fecha_cierre   date,
  saldo_actual   bigint
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/cuentas'
);

CREATE TABLE IF NOT EXISTS minio.banking.movimiento (
  codigo_movimiento      integer,
  codigo_cuenta          bigint,
  numero_movimiento      smallint,
  fecha_operacion        timestamp(3),
  importe                decimal(17,0),
  codigo_tipo_movimiento bigint,
  comprobante            bigint
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/movimiento'
);

CREATE TABLE IF NOT EXISTS minio.banking.tasas_interes (
  codigo_tasa smallint,
  tipo_tasa   varchar(60),
  tasa        decimal(4,2)
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/tasas_interes'
);

CREATE TABLE IF NOT EXISTS minio.banking.tipos_cuentas (
  codigo_tipo integer,
  tipo_cuenta varchar(30)
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/tipos_cuentas'
);

CREATE TABLE IF NOT EXISTS minio.banking.tipos_movimiento (
  codigo_tipo_movimiento integer,
  descripcion            varchar(30),
  suma                   boolean
)
WITH (
  format = 'PARQUET',
  external_location = 's3a://bronze/banking/tipos_movimiento'
);
