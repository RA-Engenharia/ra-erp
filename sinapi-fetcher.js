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

// Converte "1,071.33" / "280.81" / "-" → number (formato US: vírgula=milhar, ponto=decimal)
const parsePrecoUS = (v) => {
    if (v === undefined || v === null) return 0;
    const s = String(v).trim();
    if (s === '' || s === '-') return 0;
    return parseFloat(s.replace(/,/g, '')) || 0;
};

// Parser ESPECÍFICO do SINAPI_Referência (layout real da CAIXA):
// - Abas CSD/CCD (composições) e ISD/ICD (insumos), cada UF = coluna "Custo (R$)"
// - Cabeçalho real ~linha 9, dados a partir da linha 10
// - Linha com siglas de UF (AC, AL, ...) marca a coluna de cada custo
const parseSinapiReferencia = (buf, uf) => {
    if (!XLSX) throw new Error('xlsx lib não instalada');
    uf = (uf || 'MG').toUpperCase();
    const wb = XLSX.read(buf, { type: 'buffer' });
    const sheetsComposicoes = ['CSD', 'CCD']; // sem/com desoneração
    const sheetsInsumos = ['ISD', 'ICD'];
    const out = [];

    // Extrai o código real da fórmula HYPERLINK/MATCH da célula
    // (na SINAPI Referência o código fica embutido: HYPERLINK(...,104658) / MATCH(104658,...))
    const codigoDaFormula = (sheet, rowIdx, colIdx) => {
        const addr = XLSX.utils.encode_cell({ r: rowIdx, c: colIdx });
        const cell = sheet[addr];
        if (!cell) return '';
        if (cell.f) {
            // tenta MATCH(NUMERO, ... ou último argumento numérico
            const mMatch = cell.f.match(/MATCH\((\d{3,})/);
            if (mMatch) return mMatch[1];
            const mLast = cell.f.match(/,(\d{3,})\)\s*$/);
            if (mLast) return mLast[1];
        }
        // fallback: valor da célula se for número não-zero
        if (cell.v && cell.v !== 0) return String(cell.v);
        return '';
    };

    const processarSheet = (sheetName, ehComposicao) => {
        const sheet = wb.Sheets[sheetName];
        if (!sheet) return 0;
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', raw: false });
        if (rows.length < 11) return 0;

        // 1. Acha a linha de cabeçalho (contém "Código" e "Descrição")
        let headerRow = -1;
        for (let i = 0; i < Math.min(rows.length, 15); i++) {
            const joined = rows[i].map(c => String(c)).join('|').toLowerCase();
            if (joined.includes('código') && joined.includes('descri') && joined.includes('unidade')) {
                headerRow = i; break;
            }
        }
        if (headerRow < 0) return 0;

        // 2. Acha a coluna da UF: procura nas linhas próximas ao header uma célula == UF
        let ufCol = -1;
        for (let i = Math.max(0, headerRow - 7); i <= headerRow + 1; i++) {
            if (!rows[i]) continue;
            for (let c = 0; c < rows[i].length; c++) {
                if (String(rows[i][c]).trim().toUpperCase() === uf) { ufCol = c; break; }
            }
            if (ufCol >= 0) break;
        }
        // Se não achou a UF, usa a primeira coluna "Custo (R$)" após Unidade
        if (ufCol < 0) {
            const hdr = rows[headerRow].map(c => String(c).toLowerCase());
            ufCol = hdr.findIndex(h => h.includes('custo'));
        }
        if (ufCol < 0) return 0;

        // 3. Mapeia colunas fixas pelo header
        const hdr = rows[headerRow].map(c => String(c).toLowerCase().replace(/\s+/g, ' '));
        const colCodigo = hdr.findIndex(h => h.includes('código') || h.includes('codigo'));
        const colDesc = hdr.findIndex(h => h.includes('descri'));
        const colUnid = hdr.findIndex(h => h.includes('unidade'));
        if (colCodigo < 0 || colDesc < 0) return 0;

        // 4. Extrai dados
        let count = 0;
        for (let i = headerRow + 1; i < rows.length; i++) {
            const r = rows[i];
            if (!r) continue;
            let codigo = String(r[colCodigo] || '').trim();
            // Se código veio 0/vazio, extrai da fórmula HYPERLINK/MATCH da célula
            if (!codigo || codigo === '0') {
                codigo = codigoDaFormula(sheet, i, colCodigo) || codigo;
            }
            const descricao = String(r[colDesc] || '').trim();
            const unidade = String(r[colUnid >= 0 ? colUnid : 3] || '').trim();
            const custo = parsePrecoUS(r[ufCol]);
            if (codigo && codigo !== '0' && descricao && custo > 0) {
                out.push({
                    codigo, descricao, unidade,
                    custoUnitario: custo,
                    tipo: ehComposicao ? 'composicao' : 'insumo',
                    fonte: sheetName
                });
                count++;
            }
        }
        return count;
    };

    // Prioriza composições sem desoneração (CSD)
    let total = 0;
    for (const sn of sheetsComposicoes) {
        const n = processarSheet(sn, true);
        if (n > 0) { total += n; break; } // usa a primeira que funcionar
    }
    // Se não houver composições, tenta insumos
    if (total === 0) {
        for (const sn of sheetsInsumos) {
            const n = processarSheet(sn, false);
            if (n > 0) { total += n; break; }
        }
    }
    return out;
};

// Parser GENÉRICO (pra outras tabelas: SICRO, SEINFRA, SBC, ORSE)
// Tenta primeiro o layout SINAPI; se falhar, usa heurística de colunas nomeadas.
const parseXlsx = (buf, uf) => {
    if (!XLSX) throw new Error('xlsx lib não instalada');
    // Tenta layout SINAPI primeiro
    try {
        const sinapi = parseSinapiReferencia(buf, uf);
        if (sinapi.length > 0) return sinapi;
    } catch (e) { /* ignora, cai no genérico */ }

    const wb = XLSX.read(buf, { type: 'buffer' });
    const composicoes = [];
    wb.SheetNames.forEach(sheetName => {
        const sheet = wb.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false });
        rows.forEach(row => {
            const codigo = row['Código'] || row['CODIGO'] || row['CÓDIGO'] || row['Codigo'] ||
                          row['Código da Composição'] || row['Código do Insumo'] || row['Cód.'] || '';
            const descricao = row['Descrição'] || row['DESCRICAO'] || row['DESCRIÇÃO'] ||
                             row['Descricao'] || row['Descrição da Composição'] ||
                             row['Descrição do Insumo'] || '';
            const unidade = row['Unidade'] || row['UN'] || row['UNIDADE'] || row['Un.'] || row['Unidade Composição'] || '';
            const custoRaw = row['Custo Total'] || row['CUSTO TOTAL'] || row['Preço'] ||
                            row['PRECO'] || row['Preço Unitário'] || row['Custo Unitário'] ||
                            row['Custo'] || row['VALOR'] || 0;
            const custo = parsePrecoUS(custoRaw) || (parseFloat(String(custoRaw).replace(/\./g, '').replace(',', '.')) || 0);
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
        if (route === '/health') {
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
                    let candidatos = itens.filter(it => {
                        const m = mesDoArquivo(it.nome);
                        return m === mes && /xlsx/i.test(it.nome);
                    });

                    // FALLBACK: se o mês solicitado não existe, usa o mais recente disponível
                    let mesUsado = mes;
                    if (candidatos.length === 0) {
                        const xlsxItens = itens.filter(it => /xlsx/i.test(it.nome) && mesDoArquivo(it.nome));
                        if (xlsxItens.length > 0) {
                            // já vem ordenado por Modified desc, então o primeiro é o mais recente
                            const maisRecente = xlsxItens.sort((a, b) => mesDoArquivo(b.nome).localeCompare(mesDoArquivo(a.nome)))[0];
                            mesUsado = mesDoArquivo(maisRecente.nome);
                            candidatos = [maisRecente];
                            console.log('[sinapi] mês ' + mes + ' indisponível — usando o mais recente: ' + mesUsado);
                        }
                    }
                    if (candidatos.length === 0) throw new Error('Nenhum XLSX SINAPI encontrado. Disponíveis: ' + itens.slice(0, 6).map(i => mesDoArquivo(i.nome)).filter(Boolean).join(', '));

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

                    console.log('[sinapi] parseando', alvo.entryName, '(UF=' + uf.toUpperCase() + ')');
                    const xlsxBuf = alvo.getData();
                    const dados = parseXlsx(xlsxBuf, uf);
                    if (dados.length === 0) throw new Error('Parser retornou 0 itens. XLSX pode ter layout diferente — abra ' + alvo.entryName + ' manualmente e verifique cabeçalhos.');

                    // Cacheia tanto no mês solicitado quanto no mês real (pra GET /dados achar)
                    [mes, mesUsado].forEach(mm => {
                        const dir = path.join(CACHE_DIR, mm);
                        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
                        const arq = cacheFile(mm, uf.toUpperCase(), 'composicoes');
                        fs.writeFileSync(arq, JSON.stringify({ mes: mesUsado, uf, tipo:'composicoes', count: dados.length, dados, fonte: arqOficial.url, arquivo: alvo.entryName }));
                    });
                    console.log('[sinapi] ok:', dados.length, 'composições (mês ' + mesUsado + ') →', cacheFile(mes, uf.toUpperCase(), 'composicoes'));

                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ ok: true, count: dados.length, mesUsado, arquivoXlsx: alvo.entryName, fonteZip: arqOficial.url }));
                } catch (err) {
                    console.error('[sinapi] erro:', err.message);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
            return;
        }

        // ── SERVING ESTÁTICO: serve index.html e arquivos da pasta ──
        // Permite acessar o ERP em http://localhost:3040/ (mesma origem do
        // backend = sem problema de CORS). Só responde GET fora das rotas /api.
        if (req.method === 'GET') {
            const MIME = {
                '.html': 'text/html; charset=utf-8', '.js': 'text/javascript',
                '.css': 'text/css', '.json': 'application/json', '.png': 'image/png',
                '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
                '.woff': 'font/woff', '.woff2': 'font/woff2'
            };
            let rel = decodeURIComponent(route);
            if (rel === '/' ) rel = '/index.html';
            // segurança: impede path traversal
            const safePath = path.normalize(path.join(__dirname, rel));
            if (safePath.startsWith(__dirname) && fs.existsSync(safePath) && fs.statSync(safePath).isFile()) {
                const ext = path.extname(safePath).toLowerCase();
                res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
                fs.createReadStream(safePath).pipe(res);
                return;
            }
        }

        res.writeHead(404); res.end(JSON.stringify({ error: 'route_not_found' }));
    } catch (err) {
        res.writeHead(500); res.end(JSON.stringify({ error: err.message }));
    }
});

server.listen(PORT, () => {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  RA ENGENHARIA ERP — Servidor Local');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  Abra o sistema em:  http://localhost:' + PORT + '/');
    console.log('');
    console.log('  Backend SINAPI + Web na mesma porta (sem CORS).');
    console.log('  Cache:', CACHE_DIR);
    console.log('  Libs: xlsx ' + (XLSX ? '✓' : '✗ npm install xlsx') +
                '  | adm-zip ' + (AdmZip ? '✓' : '✗ npm install adm-zip'));
    console.log('');
    console.log('  Endpoints API: /sinapi/listar-oficial, /sinapi/baixar,');
    console.log('                 /sinapi/dados, /tabela/importar, /tabela/dados');
    console.log('');
    console.log('  Pode FECHAR esta janela quando terminar de usar o sistema.');
    console.log('  (Ctrl+C para parar)');
    console.log('═══════════════════════════════════════════════════════════════');
});
