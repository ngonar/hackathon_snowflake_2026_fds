import http from 'http';
import https from 'https';
import { readFileSync, existsSync, statSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join, extname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = 8080;
const API_TARGET = process.env.API_URL || 'http://remitapp-api-service.gxpx.svc.spcs.internal:8000';
const DIST_DIR = join(__dirname, 'dist');

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api')) {
    const targetPath = req.url.replace(/^\/api/, '') || '/';
    const url = new URL(API_TARGET);
    const isHttps = url.protocol === 'https:';
    const transport = isHttps ? https : http;
    const proxyHeaders = {
      host: url.hostname,
    };
    if (req.headers['content-type']) proxyHeaders['content-type'] = req.headers['content-type'];
    if (req.headers['content-length']) proxyHeaders['content-length'] = req.headers['content-length'];
    if (req.headers['authorization']) proxyHeaders['authorization'] = req.headers['authorization'];
    if (req.headers['accept']) proxyHeaders['accept'] = req.headers['accept'];

    const options = {
      hostname: url.hostname,
      port: url.port || (isHttps ? 443 : 80),
      path: targetPath,
      method: req.method,
      headers: proxyHeaders,
    };

    const proxyReq = transport.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
      console.error('Proxy error:', err.message);
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ detail: 'Backend API service unavailable. Deploy backend services first.' }));
    });

    req.pipe(proxyReq);
    return;
  }

  let filePath = join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);

  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    filePath = join(DIST_DIR, 'index.html');
  }

  const ext = extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  try {
    const content = readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch {
    res.writeHead(500);
    res.end('Internal Server Error');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
