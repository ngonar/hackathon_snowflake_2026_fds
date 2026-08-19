-- Ngonaroid FDS - SPCS Service Deployment
-- Run this after pushing Docker images with deploy.sh
-- Execute in Snowflake as ACCOUNTADMIN

USE ROLE ACCOUNTADMIN;
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA FDS;
USE WAREHOUSE COMPUTE_WH;

-- ============================================
-- 1. API Server Service
-- ============================================
CREATE SERVICE IF NOT EXISTS REMITAPP_API_SERVICE
  IN COMPUTE POOL SYSTEM_COMPUTE_POOL_CPU
  EXTERNAL_ACCESS_INTEGRATIONS = (FDS_EXTERNAL_ACCESS)
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1
  FROM SPECIFICATION $$
  spec:
    containers:
    - name: api-server
      image: /snowflake_learning_db/fds/fds_repo/remitapp-api:latest
      env:
        DATABASE_URL: "sqlite:///./remittance.db"
        SECRET_KEY: "super_secret_remittance_encryption_key_38472918"
        SNOWFLAKE_ACCOUNT: "oc88676.ap-southeast-2"
        SNOWFLAKE_USER: "ngonar"
        SNOWFLAKE_PASSWORD: "Bandunglautanasmara.1"
        SNOWFLAKE_WAREHOUSE: "SNOWFLAKE_LEARNING_WH"
        SNOWFLAKE_DATABASE: "SNOWFLAKE_LEARNING_DB"
        SNOWFLAKE_SCHEMA: "FDS"
        SNOWFLAKE_ROLE: "ACCOUNTADMIN"
      readinessProbe:
        port: 8000
        path: /
      resources:
        requests:
          cpu: 0.5
          memory: 512M
        limits:
          cpu: 1
          memory: 1G
    endpoints:
    - name: api-endpoint
      port: 8000
      public: true
  $$;

-- ============================================
-- 2. MCP Server Service
-- ============================================
CREATE SERVICE IF NOT EXISTS REMITAPP_MCP_SERVICE
  IN COMPUTE POOL SYSTEM_COMPUTE_POOL_CPU
  EXTERNAL_ACCESS_INTEGRATIONS = (FDS_EXTERNAL_ACCESS)
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1
  FROM SPECIFICATION $$
  spec:
    containers:
    - name: mcp-server
      image: /snowflake_learning_db/fds/fds_repo/remitapp-mcp:latest
      env:
        REMIT_API_URL: "http://REMITAPP_API_SERVICE:8000"
        FASTMCP_PORT: "8001"
        FASTMCP_HOST: "0.0.0.0"
      readinessProbe:
        port: 8081
        path: /health
      resources:
        requests:
          cpu: 0.5
          memory: 512M
        limits:
          cpu: 1
          memory: 1G
    endpoints:
    - name: mcp-endpoint
      port: 8001
      public: true
  $$;

-- ============================================
-- 3. FDS Agent Service
-- ============================================
CREATE SERVICE IF NOT EXISTS FDS_AGENT_SERVICE
  IN COMPUTE POOL SYSTEM_COMPUTE_POOL_CPU
  EXTERNAL_ACCESS_INTEGRATIONS = (FDS_EXTERNAL_ACCESS)
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1
  FROM SPECIFICATION $$
  spec:
    containers:
    - name: fds-agent
      image: /snowflake_learning_db/fds/fds_repo/fds-agent:latest
      env:
        SNOWFLAKE_ACCOUNT: "oc88676.ap-southeast-2"
        SNOWFLAKE_USER: "ngonar"
        SNOWFLAKE_PASSWORD: "Bandunglautanasmara.1"
        SNOWFLAKE_WAREHOUSE: "SNOWFLAKE_LEARNING_WH"
        SNOWFLAKE_DATABASE: "SNOWFLAKE_LEARNING_DB"
        SNOWFLAKE_SCHEMA: "FDS"
        SNOWFLAKE_ROLE: "ACCOUNTADMIN"
        FDS_DB_PATH: "/app/fds.db"
        REMIT_DB_PATH: "/app/remittance.db"
        SF_POLL_INTERVAL: "5"
        MCP_SERVER_URL: "http://REMITAPP_MCP_SERVICE:8001/mcp"
      readinessProbe:
        port: 8080
        path: /
      resources:
        requests:
          cpu: 0.5
          memory: 1G
        limits:
          cpu: 1
          memory: 2G
    endpoints:
    - name: fds-endpoint
      port: 8080
      public: true
  $$;

-- ============================================
-- 4. Grant public endpoint access
-- ============================================
GRANT USAGE ON SERVICE REMITAPP_API_SERVICE TO ROLE ACCOUNTADMIN;
GRANT USAGE ON SERVICE REMITAPP_MCP_SERVICE TO ROLE ACCOUNTADMIN;
GRANT USAGE ON SERVICE FDS_AGENT_SERVICE TO ROLE ACCOUNTADMIN;

-- ============================================
-- 5. Verify deployment
-- ============================================
SHOW SERVICES IN SCHEMA SNOWFLAKE_LEARNING_DB.FDS;
-- Check endpoints:
-- SHOW ENDPOINTS IN SERVICE REMITAPP_API_SERVICE;
-- SHOW ENDPOINTS IN SERVICE REMITAPP_MCP_SERVICE;
-- SHOW ENDPOINTS IN SERVICE FDS_AGENT_SERVICE;
-- Check status:
-- SELECT SYSTEM$GET_SERVICE_STATUS('SNOWFLAKE_LEARNING_DB.FDS.REMITAPP_API_SERVICE');
-- SELECT SYSTEM$GET_SERVICE_STATUS('SNOWFLAKE_LEARNING_DB.FDS.REMITAPP_MCP_SERVICE');
-- SELECT SYSTEM$GET_SERVICE_STATUS('SNOWFLAKE_LEARNING_DB.FDS.FDS_AGENT_SERVICE');
