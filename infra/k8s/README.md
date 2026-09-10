# Manifiestos de Kubernetes

Despliegue equivalente a `docker-compose.yml`, pensado para un cluster local
(`kind` o `minikube`). **No se ejecutó en un cluster real durante el
desarrollo de este proyecto** (no había uno disponible en el entorno donde
se generó el código) — se entrega como manifiesto validado sintácticamente,
pendiente de verificación end-to-end por quien lo despliegue.

## Orden de aplicación

```bash
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl apply -f infra/k8s/01-configmap.yaml -f infra/k8s/02-secrets.yaml
kubectl apply -f infra/k8s/10-redis.yaml -f infra/k8s/11-rabbitmq.yaml -f infra/k8s/12-itinerary-db.yaml
kubectl apply -f infra/k8s/20-airport-service.yaml -f infra/k8s/21-itinerary-service.yaml
kubectl apply -f infra/k8s/22-api-gateway.yaml -f infra/k8s/23-notification-bridge.yaml
kubectl apply -f infra/k8s/30-frontend.yaml
```

O simplemente `kubectl apply -f infra/k8s/` (los prefijos numéricos ya
ordenan las dependencias razonablemente).

## Antes de aplicar

Las imágenes referenciadas (`itinerarios/<servicio>:latest`) deben existir
en el cluster. Con `kind`:

```bash
docker compose build
kind load docker-image itinerarios-app-airport-service:latest --name <cluster>
# repetir por cada servicio, o usar un registry local
```

No se incluyen `LocalStack`, `Vault`, `Toxiproxy`, `Jaeger`, `Prometheus` ni
`Grafana` en estos manifiestos: en un cluster real esas piezas de
infraestructura compartida normalmente se instalan como charts de Helm
independientes, fuera del alcance de este ejercicio académico — para
verificar el sistema completo (incluidas esas piezas), usar
`docker compose up` (ver README raíz).
