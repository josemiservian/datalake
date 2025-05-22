create table if not exists iceberg.silver.snbe 
with (
    location = 's3a://silver/snbe/',
    format = 'parquet',
    partitioning = array['fecha_evento'],
    sorted_by = array['fechahoraevento']
)
as 
select 
	serialtarjeta,
	idsam,
	cast(date_parse(fechahoraevento, '%Y/%m/%d %H:%i:%s.%f') as timestamp(6)) as fechahoraevento,
	producto, 
	cast(montoevento as integer) as montoevento,
	cast(consecutivoevento as integer) as consecutivoevento,
	cast(identidad as integer) as identidad,
	cast(tipoevento as integer) as tipoevento,
	cast(latitude as double) as latitude,
	cast(longitude as double) as longitude,
	idrutaestacion,
	cast(tipotransporte as integer) as tipotransporte,
	cast(date_parse(substr(fechahoraevento, 1, 19), '%Y/%m/%d %H:%i:%S') as date) as fecha_evento
from minio.bronze.snbe
where 1 = 0