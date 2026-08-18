#!/usr/bin/env bash
set -euo pipefail
# MODIFIED: set -euo pipefail added — stops the script on the first real
# failure (e.g. a broken docker build) instead of silently continuing into
# later steps with a stale/missing image.

CLUSTER_NAME="kind"
NAMESPACE="django-stack"

echo "== 1. Cleaning up stale port-forwards and namespace =="
pkill -f "kubectl port-forward" || true
# NOTE: these two prune commands are SYSTEM-WIDE — they remove unused
# images/containers/volumes for ALL Docker projects on this machine, not
# just django-app. Kept as-is since you didn't ask to change it, just
# flagging in case that's more than intended.
docker image prune -a -f
docker system prune -a --volumes -f
# MODIFIED: added `|| true` — deleting a namespace that doesn't exist yet
# (first run) would otherwise error before the rest of the script runs.
kubectl delete namespace "${NAMESPACE}" || true

echo "== 2. Ensuring Kind cluster '${CLUSTER_NAME}' exists =="
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    kind create cluster --name "${CLUSTER_NAME}"
fi
kubectl config use-context "kind-${CLUSTER_NAME}"

echo "== 3. Creating namespace '${NAMESPACE}' =="
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "== 4. Building and loading image =="
docker build -t django-app:dev .
kind load docker-image django-app:dev --name "${CLUSTER_NAME}"

echo "== 5. Applying manifests =="
kubectl apply -f k8s.yaml -n "${NAMESPACE}"

echo "== 6. Waiting for app rollout =="
kubectl rollout status deployment/app -n "${NAMESPACE}" --timeout=180s

# Everything below is printed only — not executed. Same content and
# structure as your original: manual next steps for port-forwarding,
# migrations, tests, and Trivy scans.
echo '
== 7. Running Django migrations, seed, and tests
kubectl exec deployment/app -n django-stack -- python manage.py migrate
kubectl exec deployment/app -n django-stack -- python manage.py seed
kubectl exec deployment/app -n django-stack -- python manage.py test --settings=app.settings_test

== 8. Display current pod statuses
kubectl get pods -n django-stack -w

== 9. Trivy Privilege Escalation scan on the current directory
trivy config --quiet --include-non-failures Dockerfile | grep -E "(DS-0002|DS-0006|DS-0027)"
trivy config --quiet --include-non-failures k8s.yaml | grep -E "(KSV-0001|KSV-0003|KSV-0005|KSV-0012|KSV-0014)"

== 10. test via terminal
curl -I http://localhost:8080

== 11. Start port-forwarding in the background
kubectl port-forward --address 0.0.0.0 svc/app 8080:8000 -n django-stack &
kubectl port-forward --address 0.0.0.0 svc/db 3308:3306 -n django-stack &
kubectl port-forward --address 0.0.0.0 svc/redis 6380:6379 -n django-stack &

== 12. Cleanup: stop port-forwarding
pkill -f "kubectl port-forward"
'

echo "== Current pod statuses =="
kubectl get pods -n "${NAMESPACE}"