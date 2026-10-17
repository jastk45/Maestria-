#!/usr/bin/env bash
# Demo de la sesión 17 — levanta un Langfuse autoalojado en esta máquina, con Docker.
#
#   ./levantar_langfuse.sh            # la primera vez baja el compose y ~4 GB de imágenes
#   ./levantar_langfuse.sh --apagar   # detiene los contenedores y CONSERVA las trazas
#   ./levantar_langfuse.sh --borrar   # BORRA los volúmenes: TODOS los proyectos y trazas (pide confirmar;
#                                     #   --borrar --si no pregunta)
#
# Qué hace, en orden:
#  1. Baja el docker-compose.yml OFICIAL de Langfuse en una versión fijada (no se versiona
#     en el repositorio: lo reconstruye este script) y fija también la imagen, que el
#     compose oficial pide por la etiqueta flotante «:4».
#  2. Ata los puertos a 127.0.0.1: en el aula la red es compartida y la demo no tiene por
#     qué ser visible desde otra máquina.
#     Y quita los puertos de los servicios internos (Postgres, Redis, ClickHouse, el
#     worker): hablan entre sí por la red de Docker, y en el host solo chocan con un
#     Postgres que ya esté en el 5432. Quedan la web (3000) y MinIO (9090, el SDK sube ahí).
#  3. Genera, solo la primera vez, los secretos del servidor y un proyecto con sus claves
#     (inicialización headless de Langfuse) en .langfuse/.env, y copia las dos claves y la
#     URL a ./.env para demo.py. Los dos .env están en .gitignore: ninguna clave llega al
#     repositorio (curso/politica-credenciales.md).
#
# Documentación: https://langfuse.com/self-hosting/deployment/docker-compose y
# https://langfuse.com/self-hosting/administration/headless-initialization, consultadas el
# 2026-10-06 (fuentes/web/fuentes-web.md). Docker Compose «lacks high-availability, scaling
# capabilities, and backup functionality»: sirve para probar y para una clase, no para
# producción.
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${LANGFUSE_SERVER_VERSION:-4.50.0}"   # publicada el 2026-10-02
DIR=.langfuse
PROYECTO=langfuse-mmia
compose() { docker compose --project-name "$PROYECTO" --env-file "$DIR/.env" \
                -f "$DIR/docker-compose.yml" -f "$DIR/sin-puertos-internos.yml" "$@"; }

case "${1:-}" in
  --apagar) compose stop; exit 0 ;;
  --borrar)
    # down -v borra los volúmenes: TODOS los proyectos del servidor, no solo el de la demo.
    # El de la demo vuelve con las mismas claves; uno creado en la interfaz (p. ej. el del
    # solver de la semana 3) no vuelve. Pasó el 2026-10-06: por eso se pide confirmación.
    if [ "${2:-}" != "--si" ]; then
      echo "Esto borra TODOS los proyectos y trazas de este Langfuse, no solo los de la demo." >&2
      printf "Escribe BORRAR para seguir: " >&2
      read -r respuesta
      [ "$respuesta" = "BORRAR" ] || { echo "No se borró nada." >&2; exit 1; }
    fi
    compose down -v; exit 0 ;;
esac

docker info >/dev/null 2>&1 || { echo "Docker no está corriendo: abre Docker Desktop y vuelve a intentarlo." >&2; exit 1; }
mkdir -p "$DIR"

if [ ! -f "$DIR/docker-compose.yml" ]; then
  curl -sSfL "https://raw.githubusercontent.com/langfuse/langfuse/v$VERSION/docker-compose.yml" \
       -o "$DIR/docker-compose.yml"
  sed -i.orig -E \
      -e "s#(langfuse/langfuse(-worker)?):4\$#\1:$VERSION#" \
      -e 's#^( *- )([0-9]+:[0-9]+)$#\1127.0.0.1:\2#' \
      "$DIR/docker-compose.yml"
fi

cat > "$DIR/sin-puertos-internos.yml" <<'YAML'
services:
  postgres: { ports: !reset [] }
  redis: { ports: !reset [] }
  clickhouse: { ports: !reset [] }
  langfuse-worker: { ports: !reset [] }
YAML

if [ ! -f "$DIR/.env" ]; then
  PK="pk-lf-$(openssl rand -hex 16)"
  SK="sk-lf-$(openssl rand -hex 16)"
  umask 077
  cat > "$DIR/.env" <<EOF
# Generado por levantar_langfuse.sh el $(date +%F). Local, de prueba, fuera de git.
NEXTAUTH_SECRET=$(openssl rand -hex 32)
SALT=$(openssl rand -hex 16)
ENCRYPTION_KEY=$(openssl rand -hex 32)
LANGFUSE_INIT_ORG_ID=mmia
LANGFUSE_INIT_ORG_NAME=MMIA 6013
LANGFUSE_INIT_PROJECT_ID=demo-s17
LANGFUSE_INIT_PROJECT_NAME=Demo sesion 17
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=$PK
LANGFUSE_INIT_PROJECT_SECRET_KEY=$SK
LANGFUSE_INIT_USER_EMAIL=profesor@demo.local
LANGFUSE_INIT_USER_NAME=Profesor
LANGFUSE_INIT_USER_PASSWORD=$(openssl rand -hex 12)
EOF
  touch .env
  grep -v '^LANGFUSE_\(PUBLIC_KEY\|SECRET_KEY\|BASE_URL\)=' .env > .env.tmp || true
  { cat .env.tmp; echo "LANGFUSE_PUBLIC_KEY=$PK"; echo "LANGFUSE_SECRET_KEY=$SK";
    echo "LANGFUSE_BASE_URL=http://localhost:3000"; } > .env
  rm -f .env.tmp
fi

compose up -d
printf "Esperando a Langfuse en http://localhost:3000 "
for _ in $(seq 1 90); do
  if curl -sf http://localhost:3000/api/public/health >/dev/null; then
    echo "· listo."
    echo "Usuario: profesor@demo.local · contraseña: la línea LANGFUSE_INIT_USER_PASSWORD de $DIR/.env"
    exit 0
  fi
  printf "."; sleep 4
done
echo; echo "Langfuse no respondió en 6 minutos. Mira: docker compose -p $PROYECTO logs langfuse-web" >&2
exit 1
