INSERT INTO iceberg.silver.snbe
SELECT 
    serialtarjeta,
    idsam,
    CAST(date_parse(fechahoraevento, '%Y/%m/%d %H:%i:%s.%f') AS TIMESTAMP(6)) AS fechahoraevento,
    producto, 
    CAST(montoevento AS INTEGER) AS montoevento,
    CAST(consecutivoevento AS INTEGER) AS consecutivoevento,
    CAST(identidad AS INTEGER) AS identidad,
    CAST(tipoevento AS INTEGER) AS tipoevento,
    cast(nullif(trim(latitude), '') as double) as latitude,
    cast(nullif(trim(longitude), '') as double) as longitude, 
    idrutaestacion,
    CAST(tipotransporte AS INTEGER) AS tipotransporte,
    CAST(date_parse(SUBSTR(fechahoraevento, 1, 19), '%Y/%m/%d %H:%i:%S') AS DATE) AS fecha_evento
FROM minio.bronze.snbe
WHERE "$path" = '{{ path }}'