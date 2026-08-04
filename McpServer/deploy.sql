-- ============================================================
-- Deploy RemitApp MCP Server to Snowflake (SPCS)
-- Run these statements in order.
-- ============================================================

-- 1. Create database and schema
CREATE DATABASE IF NOT EXISTS REMITAPP_DB;
USE DATABASE REMITAPP_DB;
CREATE SCHEMA IF NOT EXISTS REMITAPP_SCHEMA;
USE SCHEMA REMITAPP_SCHEMA;

-- 2. Create image repository
CREATE IMAGE REPOSITORY IF NOT EXISTS IMAGE_REPO;

-- Show the repository URL (you'll need this for docker push)
SHOW IMAGE REPOSITORIES IN SCHEMA;

-- 3. Create compute pool
CREATE COMPUTE POOL IF NOT EXISTS REMITAPP_MCP_POOL
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_X64_XS;

-- Wait for compute pool to be ready
DESCRIBE COMPUTE POOL REMITAPP_MCP_POOL;

-- 4. Create the SPCS service
-- NOTE: Update the image path with the actual repository URL from step 2
CREATE SERVICE REMITAPP_MCP_SERVICE
  IN COMPUTE POOL REMITAPP_MCP_POOL
  FROM SPECIFICATION $$
spec:
  containers:
    - name: mcp-server
      image: /REMITAPP_DB/REMITAPP_SCHEMA/IMAGE_REPO/remitapp-mcp:latest
      env:
        REMIT_API_URL: http://REMITAPP_API_SERVICE:8000
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
      port: 8080
      public: true
$$;

-- 5. Check service status
SHOW SERVICES IN SCHEMA;
SELECT SYSTEM$GET_SERVICE_STATUS('REMITAPP_MCP_SERVICE');

-- 6. Register as Custom MCP Server
CREATE CUSTOM MCP SERVER REMITAPP_MCP
  SERVICE = REMITAPP_MCP_SERVICE
  ENDPOINT = 'mcp-endpoint'
  PATH = '/mcp';

-- 7. Verify
SHOW CUSTOM MCP SERVERS IN SCHEMA;
DESCRIBE CUSTOM MCP SERVER REMITAPP_MCP;

-- 8. (Optional) Check logs if needed
-- SELECT SYSTEM$GET_SERVICE_LOGS('REMITAPP_MCP_SERVICE', 0, 'mcp-server');
