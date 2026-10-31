(() => {
  // Fichier ouvert par double-clic : le navigateur bloque les requêtes, il faut passer par le serveur.
  if (location.protocol === 'file:') {
    document.body.innerHTML = `
      <div class="app"><main><header class="head">
        <h1>Lancez d'abord le serveur</h1>
        <p class="sub">Dans PowerShell, depuis le dossier du projet : node nedili-degustation/server.js, puis ouvrez http://localhost:3100</p>
      </header></main></div>`;
    return;
  }

  const SCORES = ['Pas pour moi', 'Moyen', 'Bon', 'Très bon', 'Excellent'];
  const FACES = ['😖', '😕', '🙂', '😋', '🤩'];
  const SHORT = ['Bof', 'Moyen', 'Bon', 'Très bon', 'Top'];
  const ICON_CHEVRON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>';
  const ICON_CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12.5l4 4L18 8"/></svg>';

  const $ = (sel) => document.querySelector(sel);
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const store = {
    get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* navigation privée */ } },
  };

  // Efface les choix du visiteur (sauf les envois encore en attente de réseau).
  // Fait automatiquement après l'envoi, ou en ouvrant la page avec ?nouveau pour tester.
  function resetVisitor() {
    try {
      Object.keys(localStorage).filter((k) => k.startsWith('nedili.') && k !== 'nedili.queue').forEach((k) => localStorage.removeItem(k));
    } catch { /* navigation privée */ }
  }
  if (new URLSearchParams(location.search).has('nouveau')) {
    resetVisitor();
    history.replaceState(null, '', location.pathname);
  }

  function newVisitorId() {
    const id = (crypto.randomUUID && crypto.randomUUID()) || Date.now().toString(36) + Math.random().toString(36).slice(2);
    store.set('nedili.visitor', id);
    return id;
  }
  let visitorId = store.get('nedili.visitor', null) || newVisitorId();

  let data = null;
  let ratings = store.get('nedili.ratings', {});
  let queue = store.get('nedili.queue', []);
  let current = null;
  let draft = null;

  const num = (p) => String(data.items.indexOf(p) + 1).padStart(2, '0');
  const catOf = (p) => data.categories.find((c) => c.id === p.category);
  const itemsOf = (catId) => data.items.filter((p) => p.category === catId);
  // Comme un panier : les notes restent sur le téléphone, modifiables, jusqu'à l'envoi final.
  const ratedItems = () => data.items.filter((p) => ratings[p.id]);
  const plural = (n, word) => `${n} ${word}${n > 1 ? 's' : ''}`;

  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('is-on');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => t.classList.remove('is-on'), 2000);
  }

  // Envoi : file d'attente locale si le réseau du salon décroche
  async function post(url, body) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok && res.status >= 500) throw new Error('server');
    return res;
  }

  async function flushQueue() {
    if (flushQueue.busy) return;
    flushQueue.busy = true;
    while (queue.length) {
      try { await post('/api/ratings', queue[0]); } catch { break; }
      queue.shift();
      store.set('nedili.queue', queue);
    }
    flushQueue.busy = false;
  }

  function persist() {
    store.set('nedili.ratings', ratings);
  }

  // Envoie toutes les notes d'un coup quand le visiteur valide, puis remet la page à zéro :
  // la prochaine ouverture repart sur un sondage vierge.
  function submitAndReset() {
    for (const p of ratedItems()) {
      const { score, buy, tags, comment } = ratings[p.id];
      queue.push({ visitorId, productId: p.id, score, buy, tags, comment });
    }
    store.set('nedili.queue', queue);
    flushQueue();
    resetVisitor();
    ratings = {};
    visitorId = newVisitorId();
    $('#contactForm').reset();
  }

  function removeRating(id) {
    if (!ratings[id]) return;
    delete ratings[id];
    persist();
    toast('Note retirée');
  }

  // 1. Catégories
  function renderHome() {
    $('#cats').innerHTML = data.categories.map((c) => {
      const items = itemsOf(c.id);
      const done = items.filter((p) => ratings[p.id]).length;
      const status = done === items.length
        ? `<span class="cat__badge is-done">${ICON_CHECK}Tout noté</span>`
        : done ? `<span class="cat__badge">${done}/${items.length} notés</span>` : '';
      return `
        <a class="cat" href="#c-${c.id}" style="--c:${c.color};--ink:${c.ink}">
          <span class="cat__media"><img src="${esc(c.image)}" alt=""></span>
          <span class="cat__body">
            <b>${esc(c.label)}</b>
            <small>${items.length} produit${items.length > 1 ? 's' : ''}</small>
            ${status}
          </span>
          <span class="cat__go">${ICON_CHEVRON}</span>
        </a>`;
    }).join('');
  }

  // 2. Produits d'une catégorie
  function renderCategory(cat) {
    const items = itemsOf(cat.id);
    const done = items.filter((p) => ratings[p.id]).length;
    $('#catMeta').textContent = `${done}/${items.length} notés`;
    $('#catTitle').textContent = cat.title;
    $('#prods').innerHTML = items.map((p) => {
      const r = ratings[p.id];
      return `
        <a class="prod ${r ? 'is-rated' : ''}" href="#p-${p.id}">
          <span class="prod__media"><img src="${esc(p.image)}" alt="" loading="lazy"><i>${num(p)}</i></span>
          <span class="prod__info">
            <b>${esc(p.name)}</b>
            <small>${r ? `${SCORES[r.score - 1]} · à valider` : esc(p.note)}</small>
          </span>
          ${r ? `<span class="prod__face" title="${SCORES[r.score - 1]}">${FACES[r.score - 1]}</span>` : `<span class="prod__go">${ICON_CHEVRON}</span>`}
        </a>`;
    }).join('');
  }

  // 3. Notation
  function nextUnrated(p) {
    const items = itemsOf(p.category);
    const after = [...items.slice(items.indexOf(p) + 1), ...items.slice(0, items.indexOf(p))];
    return after.find((x) => !ratings[x.id]) || null;
  }

  function renderProduct(p) {
    current = p;
    const r = ratings[p.id];
    draft = { buy: r?.buy || null, tags: [...(r?.tags || [])], comment: r?.comment || '' };
    const cat = catOf(p);
    $('#prodBack').href = $('#prodBackBottom').href = `#c-${cat.id}`;
    $('#prodBackLabel').textContent = cat.label;
    $('#prodMeta').textContent = `N° ${num(p)}`;
    $('#prodImg').src = p.image || '';
    $('#prodName').textContent = p.name;
    $('#prodNote').textContent = p.note;
    $('#comment').value = draft.comment;
    $('#tags').innerHTML = (data.tags[p.category] || []).map((t) =>
      `<button type="button" class="tag" data-tag="${esc(t)}" aria-pressed="false">${esc(t)}</button>`
    ).join('');
    renderRate();
    syncDetails();
  }

  function renderRate() {
    const r = ratings[current.id];
    $('#rate').className = `rate ${r ? 'has-score' : ''}`;
    $('#rate').innerHTML = SCORES.map((label, i) => {
      const on = r?.score === i + 1;
      return `<button type="button" role="radio" data-score="${i + 1}" aria-label="${label}" aria-checked="${on}" class="${on ? 'is-on' : ''}"><span class="face" aria-hidden="true">${FACES[i]}</span><small>${SHORT[i]}</small></button>`;
    }).join('');
    $('#details').hidden = !r;
    const next = r && nextUnrated(current);
    $('#validate').textContent = next ? 'Ajouter et noter le suivant' : 'Ajouter à mes notes';
  }

  function syncDetails() {
    document.querySelectorAll('#buy button').forEach((b) => {
      const on = draft.buy === b.dataset.value;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-checked', on);
    });
    document.querySelectorAll('.tag').forEach((t) => {
      const on = draft.tags.includes(t.dataset.tag);
      t.classList.toggle('is-on', on);
      t.setAttribute('aria-pressed', on);
    });
  }

  function rate(score) {
    const first = !ratings[current.id];
    ratings[current.id] = { buy: null, tags: [], comment: '', ...ratings[current.id], score };
    persist();
    renderRate();
    renderProgress();
    if (first) setTimeout(() => $('#details').scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 150);
  }

  // Garde l'avis détaillé s'il a changé (au clic sur Ajouter ou en quittant la fiche).
  function commitDraft() {
    if (!current || !ratings[current.id]) return false;
    const r = ratings[current.id];
    const next = { buy: draft.buy, tags: draft.tags, comment: $('#comment').value.trim() };
    if (r.buy === next.buy && r.comment === next.comment && r.tags.join() === next.tags.join()) return false;
    ratings[current.id] = { ...r, ...next };
    persist();
    return true;
  }

  function validate() {
    commitDraft();
    const next = nextUnrated(current);
    toast('Ajouté à vos notes');
    location.hash = next ? `p-${next.id}` : `c-${current.category}`;
  }

  function unrate() {
    const { id, category } = current;
    current = null;
    removeRating(id);
    location.hash = `c-${category}`;
  }

  // Fin : le « panier » des notes à valider, contact facultatif, puis remerciement
  function renderDone() {
    const rated = ratedItems();
    $('#doneSummary').textContent = rated.length
      ? 'Vérifiez vos notes avant de les envoyer. Touchez un produit pour modifier sa note, ou la croix pour la retirer.'
      : 'Aucune note pour l\'instant. Notez un produit pour l\'ajouter ici.';
    $('#recap').hidden = !rated.length;
    $('#recap').innerHTML = rated.map((p) => {
      const r = ratings[p.id];
      return `
        <li>
          <a class="recap__item" href="#p-${p.id}">
            <img src="${esc(p.image || '')}" alt="">
            <span>${esc(p.name)}<small>${SCORES[r.score - 1]} · modifier</small></span>
            <b title="${SCORES[r.score - 1]}">${FACES[r.score - 1]}</b>
          </a>
          <button class="recap__remove" type="button" data-remove="${p.id}" aria-label="Retirer la note de ${esc(p.name)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>
          </button>
        </li>`;
    }).join('');
    syncSubmit();
  }

  // Le bouton final s'adapte : envoyer les notes, les coordonnées seules, ou simplement terminer.
  function syncSubmit() {
    const n = ratedItems().length;
    $('#submitAll').textContent = n
      ? `Envoyer ${n > 1 ? `mes ${n} notes` : 'ma note'}`
      : $('#cContact').value.trim() ? 'Envoyer mes coordonnées' : 'Terminer';
    $('#addMore').hidden = !n;
  }

  async function submitAll(e) {
    e?.preventDefault();
    const f = $('#contactForm');
    const msg = $('#contactMsg');
    msg.textContent = '';
    const contact = f.contact.value.trim();
    if (contact && !f.consent.checked) {
      msg.textContent = 'Cochez la case pour recevoir nos offres et nouveautés, ou videz le champ.';
      return;
    }
    if (contact) {
      const isEmail = contact.includes('@');
      try {
        const res = await post('/api/contacts', {
          visitorId, consent: true, name: f.name.value.trim(),
          email: isEmail ? contact : '', phone: isEmail ? '' : contact,
        });
        if (!res.ok) throw new Error();
      } catch {
        msg.textContent = 'L\'envoi des coordonnées a échoué. Réessayez dans un instant.';
        return;
      }
    }
    lastFaces = ratedItems().map((p) => FACES[ratings[p.id].score - 1]);
    submitAndReset();
    location.hash = 'merci';
  }

  // Émojis donnés par le visiteur qui vient d'envoyer, gardés en mémoire pour la page de remerciement.
  let lastFaces = [];
  function renderThanks() {
    const n = lastFaces.length;
    $('#thanksText').textContent = n
      ? `${n > 1 ? `Vos ${n} avis nous aident` : 'Votre avis nous aide'} à améliorer nos recettes. À très bientôt !`
      : 'À très bientôt chez NEDILI !';
    $('#thanksFaces').innerHTML = lastFaces.map((f) => `<i>${f}</i>`).join('');
    flushQueue();
  }

  function renderProgress() {
    const done = ratedItems().length;
    const total = data.items.length;
    $('#ringText').textContent = `${done}/${total}`;
    $('#ringBar').style.strokeDashoffset = 94.25 * (1 - done / total);
    $('#barText').innerHTML = `${plural(done, 'note')} <span>à valider</span>`;
  }

  // Navigation par ancre : #c-<catégorie>, #p-<produit>, #fin, #merci. Le bouton retour du téléphone fonctionne.
  function route() {
    if (current && !location.hash.startsWith(`#p-${current.id}`)) {
      commitDraft();
      current = null;
    }
    const h = location.hash.slice(1);
    const cat = h.startsWith('c-') && data.categories.find((c) => c.id === h.slice(2));
    const prod = h.startsWith('p-') && data.items.find((p) => p.id === h.slice(2));
    const view = h === 'fin' ? 'done' : h === 'merci' ? 'thanks' : prod ? 'prod' : cat ? 'cat' : 'home';

    if (view === 'home') renderHome();
    if (view === 'cat') renderCategory(cat);
    if (view === 'prod') renderProduct(prod);
    if (view === 'done') renderDone();
    if (view === 'thanks') renderThanks();

    document.querySelectorAll('.view').forEach((v) => { v.hidden = v.id !== `view-${view}`; });
    renderProgress();
    $('#bar').hidden = !ratedItems().length || ['prod', 'done', 'thanks'].includes(view);
    window.scrollTo({ top: 0 });
  }

  // Événements
  $('#rate').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (b) rate(Number(b.dataset.score));
  });
  $('#buy').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    draft.buy = draft.buy === b.dataset.value ? null : b.dataset.value;
    syncDetails();
  });
  $('#tags').addEventListener('click', (e) => {
    const b = e.target.closest('.tag');
    if (!b) return;
    const t = b.dataset.tag;
    draft.tags = draft.tags.includes(t) ? draft.tags.filter((x) => x !== t) : [...draft.tags, t];
    syncDetails();
  });
  $('#validate').addEventListener('click', validate);
  $('#unrate').addEventListener('click', unrate);
  $('#recap').addEventListener('click', (e) => {
    const b = e.target.closest('[data-remove]');
    if (!b) return;
    removeRating(b.dataset.remove);
    renderDone();
    renderProgress();
  });
  $('#contactForm').addEventListener('submit', submitAll);
  $('#contactForm').addEventListener('input', syncSubmit);
  $('#submitAll').addEventListener('click', submitAll);
  window.addEventListener('hashchange', route);
  window.addEventListener('online', flushQueue);

  // Démarrage : l'écran de chargement reste au moins le temps de son animation,
  // et jusqu'à ce que les photos des catégories soient prêtes (3 s au plus).
  const minSplash = new Promise((r) => setTimeout(r, 1600));
  const preload = (srcs) => Promise.race([
    Promise.all(srcs.map((src) => new Promise((r) => { const img = new Image(); img.onload = img.onerror = r; img.src = src; }))),
    new Promise((r) => setTimeout(r, 3000)),
  ]);

  function hideSplash() {
    const s = $('#splash');
    s.classList.add('is-out');
    setTimeout(() => s.remove(), 600);
  }

  fetch('products.json')
    .then((r) => r.json())
    .then(async (json) => {
      data = json;
      await preload(data.categories.map((c) => c.image).filter(Boolean));
      route();
      flushQueue();
    })
    .catch(() => {
      $('#cats').innerHTML = '<p class="sub">Impossible de charger les produits. Vérifiez la connexion puis rechargez la page.</p>';
    })
    .finally(() => minSplash.then(hideSplash));
})();
