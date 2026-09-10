#!/usr/bin/env bash
# Script de arranque de LocalStack (`/etc/localstack/init/ready.d`, ver
# docker-compose.yml: `./infra/localstack/init:/etc/localstack/init/ready.d`
# y `./functions:/functions`). LocalStack lo ejecuta automaticamente una vez
# que sus servicios internos estan listos.
#
# Empaqueta cada funcion (zippeando su directorio de codigo, la forma mas
# simple y mejor soportada por `awslocal lambda create-function
# --zip-file fileb://...`) y la crea/actualiza en LocalStack. Es idempotente
# a proposito: si el contenedor de LocalStack se reinicia sin perder su
# estado (o si este script se re-ejecuta por cualquier motivo), no falla por
# "function already exists" -- actualiza el codigo y la configuracion en su
# lugar.
set -euo pipefail

FUNCTIONS_DIR="/functions"
BUILD_DIR="/tmp/lambda-build"
mkdir -p "$BUILD_DIR"

deploy_function() {
  local function_name="$1"
  local source_dir="$2"
  local environment_json="$3"

  local zip_path="${BUILD_DIR}/${function_name}.zip"
  rm -f "$zip_path"

  echo "[01_create_functions] Empaquetando ${function_name} desde ${source_dir}..."
  (cd "$source_dir" && zip -q -r "$zip_path" . -x "__pycache__/*" "*.pyc")

  if awslocal lambda get-function --function-name "$function_name" >/dev/null 2>&1; then
    echo "[01_create_functions] ${function_name} ya existe, actualizando codigo y configuracion..."
    awslocal lambda update-function-code \
      --function-name "$function_name" \
      --zip-file "fileb://${zip_path}" >/dev/null

    awslocal lambda wait function-updated --function-name "$function_name"

    awslocal lambda update-function-configuration \
      --function-name "$function_name" \
      --environment "$environment_json" >/dev/null
  else
    echo "[01_create_functions] Creando ${function_name}..."
    awslocal lambda create-function \
      --function-name "$function_name" \
      --runtime python3.12 \
      --handler handler.lambda_handler \
      --role arn:aws:iam::000000000000:role/lambda-role \
      --zip-file "fileb://${zip_path}" \
      --timeout 15 \
      --environment "$environment_json" >/dev/null
  fi

  awslocal lambda wait function-active --function-name "$function_name"
  echo "[01_create_functions] ${function_name} listo."
}

# --- SendNotificationFunction (activada por evento via notification-bridge) --
deploy_function \
  "SendNotificationFunction" \
  "${FUNCTIONS_DIR}/send_notification_function" \
  '{"Variables":{"NOTIFICATION_DB_PATH":"/var/lib/localstack/notifications/notifications.db"}}'

# --- GenerateItineraryReportFunction (invocada bajo demanda) -----------------
# INTERNAL_SERVICE_TOKEN se deja vacio a proposito: es configuracion pendiente
# de este proyecto academico (ver docstring de handler.py). Si se quiere
# generar el reporte real, exporta un JWT valido antes de levantar
# LocalStack (por ejemplo en `.env`) y agregalo aqui, o actualiza la
# configuracion de la funcion despues con
# `awslocal lambda update-function-configuration`.
deploy_function \
  "GenerateItineraryReportFunction" \
  "${FUNCTIONS_DIR}/generate_itinerary_report_function" \
  '{"Variables":{"ITINERARY_SERVICE_HTTP_URL":"http://itinerary-service:8002","INTERNAL_SERVICE_TOKEN":""}}'

echo "[01_create_functions] Funciones Lambda listas en LocalStack."
