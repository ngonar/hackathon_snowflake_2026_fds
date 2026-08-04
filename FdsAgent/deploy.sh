#!/bin/bash
# FDS Agent - Deploy to Snowpark Container Services (SPCS)
# Run this script from the FdsAgent directory.
# You'll be prompted for your TOTP code during docker login.

set -e

REGISTRY="xjlgwzz-sf83754.registry.snowflakecomputing.com"
REPO="snowflake_learning_db/fds/fds_repo"
IMAGE_NAME="fds-agent"
TAG="latest"
FULL_IMAGE="${REGISTRY}/${REPO}/${IMAGE_NAME}:${TAG}"

echo "=== Step 1: Build Docker image ==="
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${TAG} .

echo ""
echo "=== Step 2: Login to Snowflake registry ==="
echo "Enter your password followed by your TOTP code when prompted."
echo "Format: YourPassword<TOTP>  (e.g., MyPass123456789)"
docker login ${REGISTRY} -u ngonar

echo ""
echo "=== Step 3: Tag and push image ==="
docker tag ${IMAGE_NAME}:${TAG} ${FULL_IMAGE}
docker push ${FULL_IMAGE}

echo ""
echo "=== Step 4: Deploy complete! ==="
echo "Image pushed to: ${FULL_IMAGE}"
echo ""
echo "Now run the following SQL in Snowflake to create the service:"
echo ""
cat <<'SQL'
CREATE SERVICE IF NOT EXISTS SNOWFLAKE_LEARNING_DB.FDS.FDS_AGENT_SERVICE
  IN COMPUTE POOL SYSTEM_COMPUTE_POOL_CPU
  FROM SPECIFICATION $$
  spec:
    containers:
    - name: fds-agent
      image: /snowflake_learning_db/fds/fds_repo/fds-agent:latest
      env:
        SNOWFLAKE_ACCOUNT: "SF83754"
        SNOWFLAKE_USER: "ngonar"
        SNOWFLAKE_PASSWORD: "Bandunglautanasmara.1"
        SNOWFLAKE_WAREHOUSE: "SNOWFLAKE_LEARNING_WH"
        SNOWFLAKE_DATABASE: "SNOWFLAKE_LEARNING_DB"
        SNOWFLAKE_SCHEMA: "FDS"
        SNOWFLAKE_ROLE: "ACCOUNTADMIN"
        FDS_DB_PATH: "/app/fds.db"
        SF_POLL_INTERVAL: "5"
      resources:
        requests:
          memory: 1Gi
          cpu: 500m
        limits:
          memory: 2Gi
          cpu: 1000m
      readinessProbe:
        port: 8080
        path: /
    endpoints:
    - name: fds-endpoint
      port: 8080
      public: true
  $$
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1;
SQL
