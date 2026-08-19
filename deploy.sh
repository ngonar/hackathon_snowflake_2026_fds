#!/bin/bash
# Ngonaroid FDS - Master Deployment Script
# Builds and pushes all Docker images to Snowflake Container Registry
# Run from the project root: ./deploy.sh

set -e

REGISTRY="ggzejzx-li33235.registry.snowflakecomputing.com"
REPO="snowflake_learning_db/fds/fds_repo"
TAG="latest"
PLATFORM="linux/amd64"
SF_USER="NGARTOONIST"
SF_PASSWORD="k9VrxYxV5pa4bR9"

echo "============================================"
echo "  Ngonaroid FDS - SPCS Deployment"
echo "============================================"
echo ""

# Step 1: Login to Snowflake registry
echo "=== Step 1: Docker login to Snowflake registry ==="
echo "${SF_PASSWORD}" | docker login ${REGISTRY} -u ${SF_USER} --password-stdin
echo ""

# Step 2: Build ApiServer
echo "=== Step 2: Building ApiServer image ==="
docker build --platform ${PLATFORM} -t remitapp-api:${TAG} ./ApiServer
docker tag remitapp-api:${TAG} ${REGISTRY}/${REPO}/remitapp-api:${TAG}
echo "  Tagged: ${REGISTRY}/${REPO}/remitapp-api:${TAG}"
echo ""

# Step 3: Build McpServer
echo "=== Step 3: Building McpServer image ==="
docker build --platform ${PLATFORM} -t remitapp-mcp:${TAG} ./McpServer
docker tag remitapp-mcp:${TAG} ${REGISTRY}/${REPO}/remitapp-mcp:${TAG}
echo "  Tagged: ${REGISTRY}/${REPO}/remitapp-mcp:${TAG}"
echo ""

# Step 4: Build FdsAgent
echo "=== Step 4: Building FdsAgent image ==="
docker build --platform ${PLATFORM} -t fds-agent:${TAG} ./FdsAgent
docker tag fds-agent:${TAG} ${REGISTRY}/${REPO}/fds-agent:${TAG}
echo "  Tagged: ${REGISTRY}/${REPO}/fds-agent:${TAG}"
echo ""

# Step 5: Push all images
echo "=== Step 5: Pushing images to Snowflake registry ==="
docker push ${REGISTRY}/${REPO}/remitapp-api:${TAG}
echo "  Pushed: remitapp-api"
docker push ${REGISTRY}/${REPO}/remitapp-mcp:${TAG}
echo "  Pushed: remitapp-mcp"
docker push ${REGISTRY}/${REPO}/fds-agent:${TAG}
echo "  Pushed: fds-agent"
echo ""

echo "============================================"
echo "  All images pushed successfully!"
echo "============================================"
echo ""
echo "Next: Run deploy_services.sql in Snowflake to create SPCS services."
echo "Then: cd ClientApp && snow app deploy to deploy the frontend."
echo ""
