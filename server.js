// Serveur de dégustation NEDILI : fichiers statiques + API de notes.
// Aucune dépendance externe, stockage en fichiers JSONL dans ./data.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const PORT = Number(process.env.PORT || process.argv[2]) || 3100;
const ADMIN_KEY = process.env.ADMIN_KEY || 'nedili-admin';
const PUBLIC_DIR = path.join(__dirname, 'public');
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const RATINGS_FILE = path.join(DATA_DIR, 'ratings.jsonl');
const CONTACTS_FILE = path.join(DATA_DIR, 'contacts.jsonl');

fs.mkdirSync(DATA_DIR, { recursive: true });

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
};

function loadProducts() {
  return JSON.parse(fs.readFileSync(path.join(PUBLIC_DIR, 'products.json'), 'utf8'));
}

function readJsonl(file) {
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((line) => { try { return JSON.parse(line); } catch { return null; } })
    .filter(Boolean);
}

function appendJsonl(file, obj) {
  fs.appendFileSync(file, JSON.stringify(obj) + '\n');
}

// Un visiteur peut modifier sa note : seule la dernière compte.
function latestRatings() {
  const byKey = new Map();
  for (const r of readJsonl(RATINGS_FILE)) byKey.set(`${r.visitorId}:${r.productId}`, r);
  return [...byKey.values()];
}

function send(res, status, body, type = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > 16 * 1024) { reject(new Error('too_large')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); }
      catch { reject(new Error('bad_json')); }
    });
    req.on('error', reject);
  });
}

const clean = (v, max) => String(v ?? '').trim().slice(0, max);
const isAdmin = (url) => url.searchParams.get('key') === ADMIN_KEY;

function computeResults() {
  const products = loadProducts();
  const ratings = latestRatings();
  const contacts = readJsonl(CONTACTS_FILE);
  const visitors = new Set(ratings.map((r) => r.visitorId));

  const perProduct = products.items.map((p) => {
    const rs = ratings.filter((r) => r.productId === p.id);
    const dist = [0, 0, 0, 0, 0];
    rs.forEach((r) => { dist[r.score - 1]++; });
    const buy = { oui: 0, peutetre: 0, non: 0 };
    rs.forEach((r) => { if (r.buy in buy) buy[r.buy]++; });
    const tags = {};
    rs.forEach((r) => (r.tags || []).forEach((t) => { tags[t] = (tags[t] || 0) + 1; }));
    return {
      ...p,
      count: rs.length,
      average: rs.length ? rs.reduce((s, r) => s + r.score, 0) / rs.length : null,
      distribution: dist,
      buy,
      tags,
      comments: rs.filter((r) => r.comment).map((r) => ({ comment: r.comment, score: r.score, at: r.at })),
    };
  });

  return {
    totals: { ratings: ratings.length, visitors: visitors.size, contacts: contacts.length },
    categories: products.categories,
    products: perProduct,
    contacts,
  };
}

function csvEscape(v) {
  const s = String(v ?? '');
  return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function exportCsv() {
  const products = loadProducts();
  const byId = Object.fromEntries(products.items.map((p) => [p.id, p]));
  const cats = Object.fromEntries(products.categories.map((c) => [c.id, c.label]));
  const header = ['date', 'visiteur', 'categorie', 'produit', 'note', 'achat', 'tags', 'commentaire'];
  const rows = latestRatings().map((r) => {
    const p = byId[r.productId] || {};
    return [r.at, r.visitorId, cats[p.category] || '', p.name || r.productId, r.score, r.buy || '', (r.tags || []).join(', '), r.comment || ''];
  });
  // Point-virgule + BOM : s'ouvre proprement dans Excel en français.
  return '﻿' + [header, ...rows].map((row) => row.map(csvEscape).join(';')).join('\r\n');
}

async function handleApi(req, res, url) {
  if (req.method === 'POST' && url.pathname === '/api/ratings') {
    const body = await readBody(req);
    const products = loadProducts();
    const product = products.items.find((p) => p.id === body.productId);
    const score = Number(body.score);
    if (!product || !Number.isInteger(score) || score < 1 || score > 5 || !body.visitorId) {
      return send(res, 400, { error: 'invalid' });
    }
    const allowedTags = products.tags[product.category] || [];
    const rating = {
      id: crypto.randomUUID(),
      at: new Date().toISOString(),
      visitorId: clean(body.visitorId, 64),
      productId: product.id,
      score,
      buy: ['oui', 'peutetre', 'non'].includes(body.buy) ? body.buy : null,
      tags: Array.isArray(body.tags) ? body.tags.filter((t) => allowedTags.includes(t)).slice(0, 8) : [],
      comment: clean(body.comment, 500),
    };
    appendJsonl(RATINGS_FILE, rating);
    return send(res, 201, { ok: true });
  }

  if (req.method === 'POST' && url.pathname === '/api/contacts') {
    const body = await readBody(req);
    if (!body.consent || !(body.email || body.phone)) return send(res, 400, { error: 'invalid' });
    appendJsonl(CONTACTS_FILE, {
      at: new Date().toISOString(),
      visitorId: clean(body.visitorId, 64),
      name: clean(body.name, 80),
      email: clean(body.email, 120),
      phone: clean(body.phone, 30),
    });
    return send(res, 201, { ok: true });
  }

  if (req.method === 'GET' && url.pathname === '/api/results') {
    if (!isAdmin(url)) return send(res, 401, { error: 'unauthorized' });
    return send(res, 200, computeResults());
  }

  if (req.method === 'GET' && url.pathname === '/api/export.csv') {
    if (!isAdmin(url)) return send(res, 401, { error: 'unauthorized' });
    res.setHeader('Content-Disposition', 'attachment; filename="nedili-degustation.csv"');
    return send(res, 200, exportCsv(), 'text/csv; charset=utf-8');
  }

  return send(res, 404, { error: 'not_found' });
}

function serveStatic(req, res, url) {
  let pathname = decodeURIComponent(url.pathname);
  if (pathname === '/') pathname = '/index.html';
  if (pathname === '/admin') pathname = '/admin.html';
  const file = path.join(PUBLIC_DIR, path.normalize(pathname));
  if (!file.startsWith(PUBLIC_DIR)) return send(res, 403, 'Forbidden', 'text/plain');
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, 'Not found', 'text/plain');
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      // Le code et les données se revalident toujours ; seules les images restent en cache.
      'Cache-Control': /\.(webp|png|jpe?g|svg|ico)$/.test(pathname) ? 'public, max-age=86400' : 'no-cache',
    });
    res.end(data);
  });
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  res.on('finish', () => console.log(`${new Date().toLocaleTimeString('fr-FR')}  ${req.method} ${url.pathname}  ${res.statusCode}`));
  try {
    if (url.pathname.startsWith('/api/')) return await handleApi(req, res, url);
    return serveStatic(req, res, url);
  } catch (e) {
    send(res, e.message === 'too_large' ? 413 : 400, { error: e.message });
  }
}).listen(PORT, () => console.log(`NEDILI dégustation sur http://localhost:${PORT}`));
