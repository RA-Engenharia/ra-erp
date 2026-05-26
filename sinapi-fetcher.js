#!/usr/bin/env node
// =============================================================================
// SINAPI Fetcher — baixa as planilhas oficiais do site da CAIXA e expõe
// como REST API consumível pelo ERP no navegador.
// =============================================================================
//
// Por que precisa: caixa.gov.br não tem CORS aberto e os arquivos XLSX são
// grandes (50-200MB), o navegador não consegue lidar direto.
//
// Uso:
//   1. Instale dependências:    npm install xlsx
//   2. Rode:                    node sinapi-fetcher.js
//   3. No ERP, configure URL:   http://localhost:3040
//   4. Endpoints disponíveis:
//      GET  /health
//      GET  /sinapi/listar           → meses disponíveis em cache local
//      POST /sinapi/baixar           { mes: '2025-01', uf: 'MG', tipo: 'composicoes' }
//      GET  /sinapi/dados?mes=YYYY-MM&uf=UF&tipo=composicoes|insumos
//
// Cache: arquivos salvos em ./sinapi-cache/{mes}/{uf}-{tipo}.json
//
// Outras tabelas (SBC, SICRO, SEINFRA, ORSE) seguem padrão similar — me peça
// pra adicionar quando quiser.
// =============================================================================

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = process.env.PORT || 3040;
const CACHE_DIR = path.join(__dirname, 'sinapi-cache');

let XLSX = null;
try { XLSX = require('xlsx'); }
catch { console.error('⚠ xlsx não instalado. Rode: npm install xlsx'); }

if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });

const cors = (res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
};

// Templates de URL da CAIXA — mudam de tempos em tempos. Confira em
// caixa.gov.br/poder-publico/modernizacao-gestao/sinapi e ajuste se necessário.
const sinapiUrl = (mes, uf, tipo) => {
    // Formato observado historicamente:
    // SINAPI_ref_<MES_NUM>-<ANO>_<UF>_Composicoes.xlsx (zipado em pastas)
    // Você precisará validar a URL atual em caixa.gov.br
    const [ano, mesNum] = mes.split('-');
    return `https://www.caixa.gov.br/Downloads/sinapi-a-partir-jul-2014-${uf.toLowerCase()}/SINAPI_ref_${mesNum}_${ano}_${uf}_${tipo === 'insumos' ? 'Insumos' : 'Composicoes'}.xlsx`;
};

const downloadBinary = (urlStr) => new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const req = https.get({
        hostname: u.hostname, path: u.pathname + u.search,
        headers: { 'User-Agent': 'Mozilla/5.0 SINAPI-Fetcher' }
    }, (res) => {
        if (res.statusCode === 302 || res.statusCode === 301) {
            return downloadBinary(res.headers.location).then(resolve).catch(reject);
        }
        if (res.statusCode !== 200) return reject(new Error('HTTP ' + res.statusCode));
        const chunks = [];
        res.on('data', c => chunks.push(c));
        res.on('end', () => resolve(Buffer.concat(chunks)));
    });
    req.on('error', reject);
    req.setTimeout(120000, () => req.destroy(new Error('timeout 120s')));
});

const parseXlsx = (buffer) => {
    if (!XLSX) throw new Error('xlsx lib não instalada');
    const wb = XLSX.read(buffer, { type: 'buffer' });
    const composicoes = [];
    wb.SheetNames.forEach(name => {
        const sheet = wb.Sheets[name];
        const json = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        json.forEach(row => {
            // Heurística: linhas com código numérico + descrição + unidade
            const codigo = row['Código'] || row['CODIGO'] || row['Código da Composição'] || row['Cód.'] || '';
            const descricao = row['Descrição'] || row['DESCRICAO'] || row['Descrição da Composição'] || '';
            const unidade = row['Unidade'] || row['UN'] || row['Un.'] || '';
            const custo = parseFloat(String(row['Custo Total'] || row['Preço'] || row['Custo'] || row['VALOR'] || 0).toString().replace(',', '.')) || 0;
            if (codigo && descricao) {
                composicoes.push({ codigo: String(codigo), descricao, unidade, custoUnitario: custo });
            }
        });
    });
    return composicoes;
};

const cacheFile = (mes, uf, tipo) => path.join(CACHE_DIR, mes, `${uf}-${tipo}.json`);

const server = http.createServer(async (req, res) => {
    cors(res);
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    const url = new URL(req.url, 'http://localhost');
    const route = url.pathname;

    try {
        if (route === '/' || route === '/health') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true, service: 'sinapi-fetcher', xlsxAvailable: !!XLSX, cache: CACHE_DIR }));
            return;
        }

        if (route === '/sinapi/listar') {
            const lista = [];
            if (fs.existsSync(CACHE_DIR)) {
                fs.readdirSync(CACHE_DIR).forEach(mes => {
                    const mesDir = path.join(CACHE_DIR, mes);
                    if (fs.statSync(mesDir).isDirectory()) {
                        fs.readdirSync(mesDir).forEach(arq => {
                            const m = arq.match(/^(\w+)-(\w+)\.json$/);
                            if (m) lista.push({ mes, uf: m[1], tipo: m[2] });
                        });
                    }
                });
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ cache: lista }));
            return;
        }

        if (route === '/sinapi/dados') {
            const mes = url.searchParams.get('mes');
            const uf = (url.searchParams.get('uf') || 'MG').toUpperCase();
            const tipo = url.searchParams.get('tipo') || 'composicoes';
            const arq = cacheFile(mes, uf, tipo);
            if (!fs.existsSync(arq)) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'not_cached', tip: 'POST /sinapi/baixar primeiro' }));
                return;
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(fs.readFileSync(arq));
            return;
        }

        if (req.method === 'POST' && route === '/sinapi/baixar') {
            const chunks = [];
            req.on('data', c => chunks.push(c));
            req.on('end', async () => {
                try {
                    const { mes, uf = 'MG', tipo = 'composicoes' } = JSON.parse(Buffer.concat(chunks).toString());
                    if (!mes) { res.writeHead(400); res.end('{"error":"mes obrigatório (YYYY-MM)"}'); return; }
                    const url = sinapiUrl(mes, uf.toUpperCase(), tipo);
                    console.log('[sinapi] baixando', url);
                    const buf = await downloadBinary(url);
                    console.log('[sinapi] parseando', buf.length, 'bytes');
                    const dados = parseXlsx(buf);
                    const dir = path.join(CACHE_DIR, mes);
                    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                    const arq = cacheFile(mes, uf.toUpperCase(), tipo);
                    fs.writeFileSync(arq, JSON.stringify({ mes, uf, tipo, count: dados.length, dados }));
                    console.log('[sinapi] ok:', dados.length, 'registros →', arq);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ ok: true, count: dados.length, arquivo: arq }));
                } catch (err) {
                    console.error('[sinapi] erro:', err.message);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message, dica: 'A URL do CAIXA mudou. Edite sinapi-fetcher.js linha sinapiUrl().' }));
                }
            });
            return;
        }

        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'route_not_found' }));
    } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
    }
});

server.listen(PORT, () => {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(' SINAPI Fetcher rodando em http://localhost:' + PORT);
    console.log(' Cache em:', CACHE_DIR);
    console.log(' xlsx lib:', XLSX ? '✓ ok' : '✗ rode `npm install xlsx`');
    console.log('');
    console.log(' Endpoints:');
    console.log('   GET  /health');
    console.log('   GET  /sinapi/listar');
    console.log('   POST /sinapi/baixar     {mes, uf, tipo}');
    console.log('   GET  /sinapi/dados?mes=YYYY-MM&uf=MG&tipo=composicoes');
    console.log('');
    console.log(' ATENÇÃO: a URL do XLSX no CAIXA muda — se "baixar" der erro,');
    console.log(' confira em caixa.gov.br/sinapi e edite sinapiUrl() neste arquivo.');
    console.log(' Ctrl+C para parar.');
    console.log('═══════════════════════════════════════════════════════════════');
});
