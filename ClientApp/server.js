import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join, extname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = 8080;
const API_TARGET_HOST = process.env.API_HOST || 'remitapp-api-service.gxpx.svc.spcs.internal';
const API_TARGET_PORT = parseInt(process.env.API_PORT || '8000');
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
    const options = {
      hostname: API_TARGET_HOST,
      port: API_TARGET_PORT,
      path: targetPath,
      method: req.method,
      headers: { ...req.headers, host: API_TARGET_HOST },
    };

    const proxyReq = http.request(options, (proxyRes) => {
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
