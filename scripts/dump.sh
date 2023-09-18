#!/bin/bash

set -euxo pipefail

# Set kube context
# kubectl config use-context ,,,

# Set kube context namespace
# kubectl config set-context --current --namespace=,,,

# Set file
FILE=fixtures

# Set source env
SRC_ENV=api-prod

# Get source pod
SRC_POD=$(kubectl get po -l app.kubernetes.io/name=$SRC_ENV -o name | head -n 1)

# Dump fixtures in source pod
kubectl exec $SRC_POD -- /bin/bash -c "\
  python manage.py dumpfixture --output $FILE.json && \
  tar -czvf $FILE.tar.gz $FILE.json\
"

# Copy fixtures from source pod
kubectl cp $SRC_POD:/app/$FILE.tar.gz ./$FILE.tar.gz

# Remove fixtures from pod
kubectl exec $SRC_POD -- rm $FILE.json $FILE.tar.gz
