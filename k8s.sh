#!/usr/bin/env bash

# 1. Kill stale background port-forwards
pkill -f "kubectl port-forward" || true
# docker image prune -a -f
# docker system prune -a --volumes -f
# kubectl delete namespace django-stack

# 2. Check if the Kind cluster exists; create it if missing
CLUSTER_NAME="kind"
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "Creating Kind cluster '${CLUSTER_NAME}'..."
    kind create cluster --name "${CLUSTER_NAME}"
else
    echo "Kind cluster '${CLUSTER_NAME}' already exists."
fi

# 3. Ensure kubectl points to the Kind cluster context
kubectl config use-context "kind-${CLUSTER_NAME}"

# 4. Create the namespace cleanly
echo "Ensuring namespace 'django-stack' exists..."
kubectl create namespace django-stack --dry-run=client -o yaml | kubectl apply -f -

# 5. Build local Docker image
echo "Building local Docker image..."
docker build -t django-app:dev .

# 6. Load the image into the Kind cluster
echo "Loading Docker image into Kind cluster..."
kind load docker-image django-app:dev --name "${CLUSTER_NAME}"

# 7. Apply Kubernetes manifests into the namespace
echo "Applying Kubernetes manifests..."
kubectl apply -f k8s.yaml -n django-stack

# 8. Wait for the Django deployment to be fully ready
echo "Waiting for app rollout to finish..."
kubectl rollout status deployment/app -n django-stack --timeout=180s

echo '
# 9. Start port-forwarding in the background
kubectl port-forward --address 0.0.0.0 svc/app 8080:8000 -n django-stack &
kubectl port-forward --address 0.0.0.0 svc/db 3308:3306 -n django-stack &
kubectl port-forward --address 0.0.0.0 svc/redis 6380:6379 -n django-stack &

# 10. Running Django migrations, seed, and tests
kubectl exec deployment/app -n django-stack -- python manage.py migrate
kubectl exec deployment/app -n django-stack -- python manage.py seed
kubectl exec deployment/app -n django-stack -- python manage.py test --settings=app.settings_test

# 11. test via terminal
curl -I http://localhost:8080
'
# 12. Display current pod statuses
kubectl get pods -n django-stack