#!/usr/bin/env node
// =============================================================================
// PlugNotas Proxy — atravessa CORS pra emitir NFS-e do navegador
// =============================================================================
// Uso:
//   node plugnotas-proxy.js
//
// Depois, no ERP em Configurações > NF-e > Configurar PlugNotas, preencha
// "Proxy URL" com http://localhost:3030
//
// Dependências: ZERO. Usa só http nativo do Node (sem npm install).
// =============================================================================

const http = require('http');
const https = require('https');
const { URL } = require('url');

const PORT = process.env.PORT || 3030;

const targetFor = (ambiente) =>
    ambiente === 'producao'
        ? 'https://api.plugnotas.com.br'
        : 'https://api.sandbox.plugnotas.com.br';

const cors = (res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-api-key, X-Forwarded-Ambiente');
    res.setHeader('Access-Control-Max-Age', '86400');
};

const server = http.createServer((req, res) => {
    cors(res);
    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }
    if (req.url === '/' || req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, service: 'plugnotas-proxy', target: targetFor('homologacao') + ' | ' + targetFor('producao') }));
        return;
    }

    // Ambiente vem do header opcional X-Forwarded-Ambiente (default homologacao)
    const ambiente = (req.headers['x-forwarded-ambiente'] || 'homologacao').toLowerCase();
    const base = targetFor(ambiente);
    const target = new URL(req.url, base);

    const opts = {
        method: req.method,
        hostname: target.hostname,
        path: target.pathname + target.search,
        headers: {
            ...req.headers,
            host: target.hostname
        }
    };
    delete opts.headers['x-forwarded-ambiente'];

    const upstream = https.request(opts, (up) => {
        res.writeHead(up.statusCode, up.headers);
        up.pipe(res);
    });

    upstream.on('error', (err) => {
        console.error('[proxy] upstream error:', err.message);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'upstream_unreachable', message: err.message }));
    });

    req.pipe(upstream);
});

server.listen(PORT, () => {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(' PlugNotas Proxy rodando em http://localhost:' + PORT);
    console.log(' Use esse URL no campo "Proxy URL" da configuração PlugNotas.');
    console.log(' Ambiente é definido pela própria configuração do ERP via');
    console.log(' header X-Forwarded-Ambiente (já enviado automaticamente).');
    console.log(' Logs aparecem aqui em tempo real.');
    console.log(' Para parar: Ctrl+C');
    console.log('═══════════════════════════════════════════════════════════════');
});
