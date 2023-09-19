#!/bin/bash

set -euxo pipefail

# Set kube context
# kubectl config use-context ,,,

# Set kube context namespace
# kubectl config set-context --current --namespace=,,,

# Set file
FILE="${FILE:-fixtures}"

# If dump doesn't exist
if [ ! -f "$FILE.tar.gz" ]; then
  # Set source env
  SRC_ENV="${SRC_ENV:-api-prod}"

  # Get source pod
  SRC_POD=$(kubectl get po -l app.kubernetes.io/name=$SRC_ENV -o name | \
    sed "s/^.\{4\}//" | \
    head -n 1\
  )

  # Dump fixtures in source pod
  kubectl exec $SRC_POD -- /bin/bash -c "\
    python manage.py dumpfixture --output $FILE.json && \
    tar -czvf $FILE.tar.gz $FILE.json\
  "

  # Copy fixtures from source pod
  kubectl cp --retries=2 $SRC_POD:/app/$FILE.tar.gz ./$FILE.tar.gz

  # Remove fixtures from source pod
  kubectl exec $SRC_POD -- rm $FILE.json $FILE.tar.gz
fi

# Set destination env
DST_ENV=""
if [[ $# -eq 1 ]]; then
  # Local
  if [[ $1 = l* ]]; then
    exit 0
  fi
  # Staging
  if [[ $1 = s* ]]; then
    DST_ENV=api-staging
  fi
  # Development
  if [[ $1 = d* ]]; then
    DST_ENV=api-development
  fi
fi
if [[ $DST_ENV = "" ]]; then
  echo "Please specify environment"
  exit 1
fi

# Get destination pod
DST_POD=$(kubectl get po -l app.kubernetes.io/name=$DST_ENV -o name | \
  sed "s/^.\{4\}//" | \
  head -n 1\
)

# Copy fixtures to destination pod
kubectl cp --retries=2 ./$FILE.tar.gz $DST_POD:/app/$FILE.tar.gz

# Load fixtures in destination pod
kubectl exec $DST_POD -- /bin/bash -c "\
  tar -xzvf $FILE.tar.gz && \
  python manage.py loadfixture $FILE.json\
"

# Remove fixtures from destination
kubectl exec $DST_POD -- rm $FILE.json $FILE.tar.gz
