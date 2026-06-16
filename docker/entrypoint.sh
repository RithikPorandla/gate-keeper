#!/usr/bin/env bash
# Container entrypoint. Dispatches on the first argument:
#   web    -> run migrations, optionally seed, then serve the API with gunicorn
#   worker -> run the Celery decisioning worker
#   seed   -> run the seed script and exit
set -euo pipefail

wait_for() {
  local host="$1" port="$2" name="$3"
  echo "Waiting for $name at $host:$port ..."
  for _ in $(seq 1 60); do
    if python -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0) if s.connect_ex(('$host',$port))==0 else sys.exit(1)"; then
      echo "$name is up."
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for $name" >&2
  exit 1
}

ROLE="${1:-web}"

case "$ROLE" in
  web)
    wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" postgres
    wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" redis
    echo "Applying database migrations ..."
    flask --app app.main db upgrade
    if [ "${SEED_ON_START:-true}" = "true" ]; then
      echo "Seeding synthetic demo data ..."
      python -m scripts.seed || echo "Seed step skipped/failed (non-fatal)."
    fi
    echo "Starting gunicorn ..."
    exec gunicorn --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-2}" --timeout 60 "app.main:app"
    ;;
  worker)
    wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" postgres
    wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" redis
    exec celery -A app.workers.celery_app:celery worker --loglevel=info --concurrency "${WORKER_CONCURRENCY:-4}"
    ;;
  seed)
    exec python -m scripts.seed
    ;;
  *)
    exec "$@"
    ;;
esac
