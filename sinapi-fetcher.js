#!/usr/bin/env node
// =============================================================================
// SINAPI Fetcher v2 — agora com URL OFICIAL CORRETA da CAIXA
// =============================================================================
// Descoberta em maio/2026: a CAIXA usa SharePoint REST API + ZIPs em
// sinapi-relatorios-mensais/. Estrutura validada:
//   - Lista:    /_api/web/lists/getbytitle('Downloads')/Items?$filter=Categoria/ID eq 888
//   - Arquivo:  /Downloads/sinapi-relatorios-mensais/SINAPI-YYYY-MM-formato-xlsx.zip
//
// Uso:
//   npm install xlsx adm-zip
//   node sinapi-fetcher.js
//
// Endpoints:
//   GET  /health
//   GET  /sinapi/listar-oficial           → lista arquivos disponíveis na CAIXA
//   POST /sinapi/baixar  {mes:'YYYY-MM'}  → baixa + descompacta + parseia
//   GET  /sinapi/dados?mes=YYYY-MM&uf=MG
//   GET  /sinapi/listar                   → meses em cache local
//   POST /tabela/importar {tabela, xlsxBase64}  → import genérico
//
// =============================================================================

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = process.env.PORT || 3040;
const CACHE_DIR = path.join(__dirname, 'sinapi-cache');

let XLSX = null, AdmZip = null;
try { XLSX = require('xlsx'); } catch { console.error('⚠ npm install xlsx'); }
try { AdmZip = require('adm-zip'); } catch { console.error('⚠ npm install adm-zip'); }

if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });

const cors = (res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Forwarded-Ambiente');
};

const downloadBinary = (urlStr, maxRedirects) => new Promise((resolve, reject) => {
    maxRedirects = maxRedirects === undefined ? 5 : maxRedirects;
    const u = new URL(urlStr);
    const lib = u.protocol === 'http:' ? http : https;
    const req = lib.get({
        hostname: u.hostname, port: u.port, path: u.pathname + u.search,
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120 Safari/537.36',
            'Accept': 'application/json;odata=verbose, application/octet-stream, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Cookie': 'security=true'
        }
    }, (res) => {
        if ((res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 303) && res.headers.location && maxRedirects > 0) {
            const next = new URL(res.headers.location, urlStr).href;
            return downloadBinary(next, maxRedirects - 1).then(resolve).catch(reject);
        }
        if (res.statusCode !== 200) return reject(new Error('HTTP ' + res.statusCode + ' em ' + urlStr));
        const chunks = [];
        res.on('data', c => chunks.push(c));
        res.on('end', () => resolve(Buffer.concat(chunks)));
        res.on('error', reject);
    });
    req.on('error', reject);
    req.setTimeout(180000, () => req.destroy(new Error('timeout 3min')));
});

// Lista arquivos SINAPI via SharePoint REST API
const listarOficialSINAPI = async () => {
    const url = "https://www.caixa.gov.br/_api/web/lists/getbytitle('Downloads')/Items"
        + "?$select=Title,Modified,File_x0020_Type,FileLeafRef,EncodedAbsUrl,Descricao,FileSizeDisplay"
        + "&$filter=Categoria/ID%20eq%20888%20and%20FSObjType%20eq%200%20and%20OData__ModerationStatus%20eq%200"
        + "&$top=200&$orderby=Modified%20desc";
    const buf = await downloadBinary(url);
    const data = JSON.parse(buf.toString('utf8'));
    return (data.d?.results || []).map(it => ({
        nome: it.FileLeafRef,
        tipo: it.File_x0020_Type,
        modificado: it.Modified,
        tamanho: parseInt(it.FileSizeDisplay) || 0,
        url: (it.EncodedAbsUrl || '').replace(/^http:/, 'https:'),
        descricao: it.Descricao
    })).filter(it => it.nome && /\.zip$/i.test(it.nome));
};

// Identifica mês a partir do nome do arquivo: SINAPI-2025-12-... ou SINAPI_2024_09_...
const mesDoArquivo = (nome) => {
    const m = nome.match(/SINAPI[-_](\d{4})[-_](\d{2})/);
    return m ? m[1] + '-' + m[2] : null;
};

// Parseia XLSX → array de composições
const parseXlsx = (buf) => {
    if (!XLSX) throw new Error('xlsx lib não instalada');
    const wb = XLSX.read(buf, { type: 'buffer' });
    const composicoes = [];
    wb.SheetNames.forEach(sheetName => {
        const sheet = wb.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false });
        rows.forEach(row => {
            // Heurística ampla: procura colunas com nomes variados
            const codigo = row['Código'] || row['CODIGO'] || row['CÓDIGO'] || row['Codigo'] ||
                          row['Código da Composição'] || row['Código do Insumo'] || row['Cód.'] || '';
            const descricao = row['Descrição'] || row['DESCRICAO'] || row['DESCRIÇÃO'] ||
                             row['Descricao'] || row['Descrição da Composição'] ||
                             row['Descrição do Insumo'] || '';
            const unidade = row['Unidade'] || row['UN'] || row['UNIDADE'] || row['Un.'] || row['Unidade Composição'] || '';
            const custoRaw = row['Custo Total'] || row['CUSTO TOTAL'] || row['Preço'] ||
                            row['PRECO'] || row['Preço Unitário'] || row['Custo Unitário'] ||
                            row['Custo'] || row['VALOR'] || 0;
            const custo = parseFloat(String(custoRaw).replace(/\./g, '').replace(',', '.')) || 0;
            if (codigo && descricao && custo > 0) {
                composicoes.push({
                    codigo: String(codigo).trim(),
                    descricao: String(descricao).trim(),
                    unidade: String(unidade).trim(),
                    custoUnitario: custo
                });
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
            res.end(JSON.stringify({
                ok: true, service: 'sinapi-fetcher v2',
                xlsxAvailable: !!XLSX, zipAvailable: !!AdmZip,
                cache: CACHE_DIR
            }));
            return;
        }

        // Lista arquivos oficiais via SharePoint API
        if (route === '/sinapi/listar-oficial') {
            const items = await listarOficialSINAPI();
            // Agrupa por mês com xlsx
            const meses = {};
            items.forEach(it => {
                const mes = mesDoArquivo(it.nome);
                if (!mes) return;
                if (!meses[mes]) meses[mes] = { mes, xlsx: null, pdf: null };
                if (/xlsx/i.test(it.nome)) meses[mes].xlsx = it;
                if (/pdf/i.test(it.nome)) meses[mes].pdf = it;
            });
            const ordenado = Object.values(meses).sort((a, b) => b.mes.localeCompare(a.mes));
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ meses: ordenado }));
            return;
        }

        // Lista cache local
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

        // Dados de uma tabela em cache
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

        // Tabela genérica (SICRO/SEINFRA/SBC/ORSE) via upload base64
        if (route === '/tabela/dados') {
            const tabela = url.searchParams.get('tabela');
            const mes = url.searchParams.get('mes') || new Date().toISOString().slice(0, 7);
            const uf = (url.searchParams.get('uf') || 'MG').toUpperCase();
            if (!tabela) { res.writeHead(400); res.end('{"error":"tabela obrigatória"}'); return; }
            const arq = cacheFile(mes, uf, tabela);
            if (!fs.existsSync(arq)) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'not_cached' }));
                return;
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(fs.readFileSync(arq));
            return;
        }

        if (req.method === 'POST' && route === '/tabela/importar') {
            const chunks = [];
            req.on('data', c => chunks.push(c));
            req.on('end', () => {
                try {
                    const body = JSON.parse(Buffer.concat(chunks).toString());
                    const { tabela, uf = 'MG', mes, xlsxBase64 } = body;
                    if (!tabela || !xlsxBase64) {
                        res.writeHead(400); res.end('{"error":"tabela e xlsxBase64 obrigatórios"}'); return;
                    }
                    const buf = Buffer.from(xlsxBase64, 'base64');
                    const dados = parseXlsx(buf);
                    const mesRef = mes || new Date().toISOString().slice(0, 7);
                    const dir = path.join(CACHE_DIR, mesRef);
                    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                    const arq = cacheFile(mesRef, uf.toUpperCase(), tabela);
                    fs.writeFileSync(arq, JSON.stringify({ tabela, mes: mesRef, uf, count: dados.length, dados }));
                    console.log('[' + tabela + '] importado:', dados.length, 'itens');
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ ok: true, tabela, count: dados.length }));
                } catch (err) {
                    res.writeHead(500); res.end(JSON.stringify({ error: err.message }));
                }
            });
            return;
        }

        // DOWNLOAD AUTOMÁTICO via SharePoint API → ZIP → descompacta → parseia
        if (req.method === 'POST' && route === '/sinapi/baixar') {
            const chunks = [];
            req.on('data', c => chunks.push(c));
            req.on('end', async () => {
                try {
                    if (!AdmZip) throw new Error('adm-zip não instalado. Rode: npm install adm-zip');
                    const { mes, uf = 'MG' } = JSON.parse(Buffer.concat(chunks).toString());
                    if (!mes) { res.writeHead(400); res.end('{"error":"mes (YYYY-MM) obrigatório"}'); return; }

                    console.log('[sinapi] listando arquivos oficiais...');
                    const itens = await listarOficialSINAPI();
                    const candidatos = itens.filter(it => {
                        const m = mesDoArquivo(it.nome);
                        return m === mes && /xlsx/i.test(it.nome);
                    });
                    if (candidatos.length === 0) throw new Error('Nenhum arquivo XLSX encontrado para ' + mes + '. Disponíveis: ' + itens.slice(0, 5).map(i => mesDoArquivo(i.nome)).filter(Boolean).join(', '));

                    const arqOficial = candidatos[0];
                    console.log('[sinapi] baixando', arqOficial.nome, '(' + Math.round(arqOficial.tamanho/1024/1024) + 'MB) de', arqOficial.url);
                    const zipBuf = await downloadBinary(arqOficial.url);
                    console.log('[sinapi] ZIP baixado:', zipBuf.length, 'bytes — descompactando...');

                    const zip = new AdmZip(zipBuf);
                    const entries = zip.getEntries();
                    console.log('[sinapi] ZIP contém', entries.length, 'arquivos');
                    entries.slice(0, 10).forEach(e => console.log('  -', e.entryName, '(' + e.header.size + 'b)'));

                    // Procura XLSX da UF, ou se tiver só um, usa esse
                    let alvo = entries.find(e => {
                        const n = e.entryName.toUpperCase();
                        return n.includes(uf.toUpperCase()) && /\.xlsx?$/i.test(n) && !/CUB/.test(n);
                    });
                    if (!alvo) {
                        // fallback: procura "SINAPI_Custo_Ref" + UF, ou qualquer xlsx grande
                        const xlsxs = entries.filter(e => /\.xlsx?$/i.test(e.entryName));
                        if (xlsxs.length === 1) alvo = xlsxs[0];
                        else if (xlsxs.length > 0) {
                            // pega o maior
                            alvo = xlsxs.sort((a, b) => b.header.size - a.header.size)[0];
                        }
                    }
                    if (!alvo) throw new Error('Não achei XLSX dentro do ZIP. Arquivos: ' + entries.slice(0,5).map(e => e.entryName).join(', '));

                    console.log('[sinapi] parseando', alvo.entryName);
                    const xlsxBuf = alvo.getData();
                    const dados = parseXlsx(xlsxBuf);
                    if (dados.length === 0) throw new Error('Parser retornou 0 itens. XLSX pode ter layout diferente — abra ' + alvo.entryName + ' manualmente e verifique cabeçalhos.');

                    const dir = path.join(CACHE_DIR, mes);
                    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                    const arq = cacheFile(mes, uf.toUpperCase(), 'composicoes');
                    fs.writeFileSync(arq, JSON.stringify({ mes, uf, tipo:'composicoes', count: dados.length, dados, fonte: arqOficial.url, arquivo: alvo.entryName }));
                    console.log('[sinapi] ok:', dados.length, 'composições →', arq);

                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ ok: true, count: dados.length, arquivoXlsx: alvo.entryName, fonteZip: arqOficial.url }));
                } catch (err) {
                    console.error('[sinapi] erro:', err.message);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
            return;
        }

        res.writeHead(404); res.end(JSON.stringify({ error: 'route_not_found' }));
    } catch (err) {
        res.writeHead(500); res.end(JSON.stringify({ error: err.message }));
    }
});

server.listen(PORT, () => {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(' SINAPI Fetcher v2 em http://localhost:' + PORT);
    console.log(' Cache:', CACHE_DIR);
    console.log(' Libs: xlsx ' + (XLSX ? '✓' : '✗ falta npm install xlsx'));
    console.log('       adm-zip ' + (AdmZip ? '✓' : '✗ falta npm install adm-zip'));
    console.log('');
    console.log(' Endpoints:');
    console.log('   GET  /health');
    console.log('   GET  /sinapi/listar-oficial    ← meses na CAIXA');
    console.log('   POST /sinapi/baixar  {mes,uf}  ← baixa+descompacta+parseia');
    console.log('   GET  /sinapi/dados?mes=YYYY-MM&uf=MG');
    console.log('   POST /tabela/importar  {tabela, xlsxBase64}');
    console.log('   GET  /tabela/dados?tabela=X&mes=Y&uf=Z');
    console.log('');
    console.log(' Pressione Ctrl+C para parar');
    console.log('═══════════════════════════════════════════════════════════════');
});
