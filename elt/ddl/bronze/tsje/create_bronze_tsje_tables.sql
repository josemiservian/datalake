CREATE TABLE minio.tsje.votantes_habilitados (
   cedula bigint COMMENT 'Número de cédula paraguaya',
   nombres varchar(100) COMMENT 'Nombres',
   apellidos varchar(100) COMMENT 'Apellidos',
   sexo varchar(1) COMMENT 'Sexo',
   fecha_nacimiento timestamp(3) COMMENT 'Fecha de nacimiento',
   fecha_inscripcion timestamp(3) COMMENT 'Fecha de inscripción',
   tipo varchar(1) COMMENT 'Tipo',
   codigo_nacionalidad bigint COMMENT 'Código de nacionalidad',
   codigo_departamento bigint COMMENT 'Código de departamento',
   descripcion_departamento varchar(50) COMMENT 'Descripción de departamento',
   codigo_distrito bigint COMMENT 'Código de distrito',
   descripcion_distrito varchar(50) COMMENT 'Descripción de distrito',
   codigo_zona bigint COMMENT 'Código de zona',
   descripcion_zona varchar(50) COMMENT 'Descripción de zona',
   codigo_local bigint COMMENT 'Código de local',
   descripcion_local varchar(50) COMMENT 'Descripción de local',
   mesa bigint COMMENT 'Mesa',
   orden bigint COMMENT 'Orden',
   tipo_voto bigint COMMENT 'Tipo de voto',
   descripcion_voto varchar(30) COMMENT 'Descripción de voto',
   es_indigena boolean COMMENT 'Es indígena',
   codigo_pueblo_indigena bigint COMMENT 'Código de pueblo indígena',
   codigo_comunidad_indigena bigint COMMENT 'Código de comunidad indígena',
   edad_padron bigint COMMENT 'Edad padrón',
   direccion_local varchar(200) COMMENT 'Dirección de local',
   latitud_local double COMMENT 'Latitud de local',
   longitud_local double COMMENT 'Longitud de local'
)
COMMENT 'Tabla de padrón electoral del Paraguay con datos demográficos y geográficos de los votantes'
WITH (
   external_location = 's3a://bronze/tsje/votantes_habilitados',
   format = 'PARQUET'
);