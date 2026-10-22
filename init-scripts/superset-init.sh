#!/bin/bash
set -e
: "${SUPERSET_DB_USER:?}" "${SUPERSET_DB_PASSWORD:?}" "${SUPERSET_ADMIN_USERNAME:?}" "${SUPERSET_ADMIN_PASSWORD:?}"

# Función para verificar PostgreSQL
check_postgres() {
    local max_retries=30
    local retry_interval=5
    
    for ((i=1; i<=max_retries; i++)); do
        if PGPASSWORD="$SUPERSET_DB_PASSWORD" psql -h postgres -U "$SUPERSET_DB_USER" -d superset -c "SELECT 1" &>/dev/null; then
            echo "[✓] PostgreSQL accesible"
            return 0
        fi
        echo "[$i/$max_retries] Esperando a PostgreSQL..."
        sleep $retry_interval
    done
    return 1
}

# Verificar conexión
if ! check_postgres; then
    echo "[X] Error: No se pudo conectar a PostgreSQL después de 30 intentos"
    exit 1
fi

# Comandos de inicialización
echo "Ejecutando migraciones..."
superset db upgrade

echo "Creando admin..."
superset fab create-admin \
  --username "$SUPERSET_ADMIN_USERNAME" \
  --firstname Admin \
  --lastname Superset \
  --email admin@superset.com \
  --password "$SUPERSET_ADMIN_PASSWORD"

echo "Inicializando..."
superset init

echo "[✓] Configuración completada"
exit 0