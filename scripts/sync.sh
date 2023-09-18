#!/bin/bash

set -euxo pipefail

# Set kube context
# kubectl config use-context ,,,

# Set kube context namespace
# kubectl config set-context --current --namespace=,,,

# Set file
FILE=fixtures

# Set destination environment
SRC_ENV=api-prod
DST_ENV=api-staging
if [[ $# -eq 1 ]]; then
  if [[ $1 = d* ]]; then
    DST_ENV=api-development
  fi
fi

# Get source and destination pods
SRC_POD=$(kubectl get po -l app.kubernetes.io/name=$SRC_ENV -o name | \
  sed "s/^.\{4\}//" | \
  head -n 1\
)
DST_POD=$(kubectl get po -l app.kubernetes.io/name=$DST_ENV -o name | \
  sed "s/^.\{4\}//" | \
  head -n 1\
)

# Dump fixtures in source pod
kubectl exec $SRC_POD -- /bin/bash -c "\
  python manage.py dumpfixture --output $FILE.json && \
  tar -czvf $FILE.tar.gz $FILE.json\
"

# Copy fixtures from source pod to destination pod
kubectl cp $SRC_POD:/app/$FILE.tar.gz $DST_POD:/app/$FILE.tar.gz

# Load fixtures in destination pod
kubectl exec $SRC_POD -- /bin/bash -c "\
  tar -xzvf $FILE.tar.gz && \
  python manage.py loadfixture $FILE.json && \
"

# Remove fixtures from pods
kubectl exec $SRC_POD -- rm $FILE.json $FILE.tar.gz
kubectl exec $DST_POD -- rm $FILE.json $FILE.tar.gz
