# Usado solo para el despliegue en Kubernetes (infra/k8s/30-frontend.yaml).
# En docker-compose.yml el contenido de esta carpeta se monta directamente
# sobre una imagen nginx genérica; aquí se empaqueta como imagen propia
# porque un cluster real necesita una imagen versionada, no un bind mount.
FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
EXPOSE 80
