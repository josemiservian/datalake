CREATE TABLE IF NOT EXISTS minio.ips.asalariados (
    id_cliente_salario_ips VARCHAR COMMENT 'Identificador único del cliente relacionado al salario IPS',
    id_entidad double COMMENT 'Identificador de la entidad o empresa asociada',
    cedula VARCHAR COMMENT 'Número de cédula de identidad paraguaya',
    ruc VARCHAR COMMENT 'Registro Único de Contribuyentes',
    apellidos VARCHAR COMMENT 'Apellidos del cliente',
    nombres VARCHAR COMMENT 'Nombres del cliente',
    fecha_entrada varchar COMMENT 'Fecha de entrada, ingreso o registro del cliente',
    patronal VARCHAR COMMENT 'Número o identificador del registro patronal',
    monto DOUBLE COMMENT 'Monto monetario del salario o aporte',
    rango VARCHAR COMMENT 'Rango de clasificación salarial o categórica'
)
COMMENT 'Tabla que almacena la información de los asalariados de IPS'
WITH (
   external_location = 's3a://bronze/ips/asalariados',
   format = 'PARQUET'
);
