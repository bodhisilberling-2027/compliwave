#!/bin/bash

# Exit on error
set -e

# Load environment variables
source .env

# Build and push Docker images
echo "Building and pushing Docker images..."
docker build -t ${DOCKER_REGISTRY}/compliwave-backend:${VERSION} ./backend
docker push ${DOCKER_REGISTRY}/compliwave-backend:${VERSION}

# Create secrets
echo "Creating Kubernetes secrets..."
kubectl create secret generic compliwave-secrets \
  --from-literal=database-url=${DATABASE_URL} \
  --from-literal=postgres-user=${POSTGRES_USER} \
  --from-literal=postgres-password=${POSTGRES_PASSWORD} \
  --from-literal=aws-access-key-id=${AWS_ACCESS_KEY_ID} \
  --from-literal=aws-secret-access-key=${AWS_SECRET_ACCESS_KEY} \
  --from-literal=aws-s3-bucket=${AWS_S3_BUCKET} \
  --from-literal=aws-region=${AWS_REGION} \
  --from-literal=azure-openai-api-key=${AZURE_OPENAI_API_KEY} \
  --from-literal=azure-openai-endpoint=${AZURE_OPENAI_ENDPOINT}

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -f kubernetes/database-deployment.yaml
kubectl apply -f kubernetes/database-service.yaml
kubectl apply -f kubernetes/backend-deployment.yaml
kubectl apply -f kubernetes/backend-service.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/compliwave-backend
kubectl wait --for=condition=available --timeout=300s statefulset/compliwave-db

echo "Deployment completed successfully!" 