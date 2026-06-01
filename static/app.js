// State
let allCards = [];
let allPokemon = [];
let activeTab = 'all';
let activeGen = null;
let activeSort = 'price-desc';
let groupByPokemon = true;
let pollInterval = null;

const TYPE_EMOJI = {
  fire: '🔥', water: '💧', grass: '🌿', electric: '⚡',
  psychic: '🔮', normal: '⬜', dark: '🌑', fairy: '🌸',
  ice: '❄️', ghost: '👻', fighting: '🥊', ground: '🌍',
  flying: '🌬️', steel: '⚙️', poison: '☠️', rock: '🪨',
  dragon: '🐉', bug: '🐛'
};

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  await Promise.all([loadPokemon(), loadCards()]);
  loadStatus();
  renderGrid();
}

async function loadPokemon() {
  const resp = await fetch('/api/pokemon');
  allPokemon = await resp.json();
}

async function loadCards() {
  const resp = await fetch('/api/cards');
  allCards = await resp.json();
}

async function loadStatus() {
  const resp = await fetch('/api/status');
  const data = await resp.json();
  const el = document.getElementById('stat-updated');
  el.textContent = data.last_update
    ? 'Actualizado: ' + new Date(data.last_update).toLocaleString('es-ES')
    : 'Nunca actualizado';
  if (data.updating || data.seeding) startPolling();
}

// ── Stats ─────────────────────────────────────────────────────────────────
function updateStats() {
  document.getElementById('stat-total').textContent = allCards.length;
  const sum = (status) => allCards
    .filter(c => c.status === status && c.price_current != null)
    .reduce((acc, c) => acc + c.price_current, 0);
  document.getElementById('stat-wishlist').textContent = '€' + sum('wishlist').toFixed(2);
  document.getElementById('stat-owned').textContent = '€' + sum('owned').toFixed(2);
}

// ── Filters ───────────────────────────────────────────────────────────────
function setTab(btn, tab) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeTab = tab;
  renderGrid();
}

function setGen(btn, gen) {
  document.querySelectorAll('.gen-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeGen = gen;
  renderGrid();
}

function setSort(value) {
  activeSort = value;
  renderGrid();
}

function setGroupBy(btn, grouped) {
  document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  groupByPokemon = grouped;
  renderGrid();
}

// Rarity ranking for sorting (higher = fancier), mirrors the seeder.
function rarityRank(rarity) {
  const r = (rarity || '').toLowerCase();
  if (r.includes('special illustration rare')) return 7;
  if (r.includes('illustration rare')) return 6;
  if (r.includes('radiant')) return 5;
  if (r.includes('holo')) return 4;
  if (r.includes('triple rare')) return 3;
  if (r.includes('double rare')) return 2;
  if (r.includes('rare')) return 1;
  return 0;
}

function sortCards(cards) {
  const arr = cards.slice();
  switch (activeSort) {
    case 'price-asc':
      return arr.sort((a, b) => (a.price_current ?? Infinity) - (b.price_current ?? Infinity));
    case 'rarity':
      return arr.sort((a, b) => rarityRank(b.rarity) - rarityRank(a.rarity)
        || (b.price_current || 0) - (a.price_current || 0));
    case 'name':
      return arr.sort((a, b) => a.card_name.localeCompare(b.card_name));
    case 'price-desc':
    default:
      return arr.sort((a, b) => (b.price_current || 0) - (a.price_current || 0));
  }
}

// ── Grid ──────────────────────────────────────────────────────────────────
function renderGrid() {
  updateStats();
  const search = document.getElementById('search-input').value.toLowerCase();
  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const pokemonById = {};
  allPokemon.forEach(p => { pokemonById[p.id] = p; });

  const filteredPokemon = allPokemon.filter(p => {
    if (activeGen !== null && p.generation !== activeGen) return false;
    if (search && !p.name.toLowerCase().includes(search)) return false;
    return true;
  });
  const visibleForPokemon = (pokemon) => allCards.filter(c => {
    if (c.pokemon_id !== pokemon.id) return false;
    if (activeTab === 'wishlist') return c.status === 'wishlist';
    if (activeTab === 'owned') return c.status === 'owned';
    return true;
  });

  if (groupByPokemon) {
    // Grouped view: one section per Pokemon, cards sorted within each group.
    for (const pokemon of filteredPokemon) {
      const cards = visibleForPokemon(pokemon);
      if (activeTab !== 'all' && cards.length === 0) continue;

      const section = document.createElement('section');
      section.className = 'pokemon-section';

      const label = document.createElement('div');
      label.className = 'section-label';
      label.textContent = cards.length ? `${pokemon.name} · ${cards.length}` : pokemon.name;
      section.appendChild(label);

      const cardsWrap = document.createElement('div');
      cardsWrap.className = 'section-cards';
      sortCards(cards).forEach(card => cardsWrap.appendChild(buildCardTile(card, pokemon)));
      cardsWrap.appendChild(buildEmptySlot(pokemon));
      section.appendChild(cardsWrap);
      grid.appendChild(section);
    }
    return;
  }

  // Global view: one flat list of every matching card, sorted across all Pokemon.
  const allowedIds = new Set(filteredPokemon.map(p => p.id));
  const visibleCards = allCards.filter(c => {
    if (!allowedIds.has(c.pokemon_id)) return false;
    if (activeTab === 'wishlist') return c.status === 'wishlist';
    if (activeTab === 'owned') return c.status === 'owned';
    return true;
  });

  const cardsWrap = document.createElement('div');
  cardsWrap.className = 'section-cards';

  sortCards(visibleCards)
    .forEach(card => cardsWrap.appendChild(buildCardTile(card, pokemonById[card.pokemon_id])));

  // In the "all" tab, Pokemon without any card still get a "+" tile to add one.
  if (activeTab === 'all') {
    const withCards = new Set(visibleCards.map(c => c.pokemon_id));
    filteredPokemon
      .filter(p => !withCards.has(p.id))
      .forEach(p => cardsWrap.appendChild(buildEmptySlot(p)));
  }
  // Trailing "+" tile to add a card for any Pokemon.
  cardsWrap.appendChild(buildEmptySlot(null));

  grid.appendChild(cardsWrap);
}

function buildEmptySlot(pokemon) {
  const el = document.createElement('div');
  el.className = 'card-empty';
  el.innerHTML = pokemon
    ? `<div class="plus">+</div><div class="empty-name">${pokemon.name}</div>`
    : '<div class="plus">+</div>';
  el.onclick = () => openAddModal(pokemon ? pokemon.name : '');
  return el;
}

function buildCardTile(card, pokemon) {
  const el = document.createElement('div');
  el.className = `card-tile ${card.status === 'owned' ? 'owned' : ''}`;
  const stale = card.price_current == null;
  el.innerHTML = `
    <div class="card-img-wrap">
      ${card.image_url
        ? `<img src="${card.image_url}" alt="${card.card_name}" loading="lazy">`
        : `<div class="card-placeholder ${typeClass(pokemon.type_1)}">${typeEmoji(pokemon.type_1)}</div>`}
    </div>
    <div class="badge ${card.status === 'owned' ? 'badge-owned' : 'badge-wishlist'}">
      ${card.status === 'owned' ? '✅' : '💜'}
    </div>
    <div class="card-info">
      <div class="card-name">${card.card_name}</div>
      <div class="card-price ${stale ? 'stale' : ''}">
        ${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}
        ${stale ? '<span class="badge badge-stale">⚠</span>' : ''}
      </div>
    </div>`;
  el.onclick = () => openDetailModal(card);
  return el;
}

function typeClass(type) {
  const t = (type || '').toLowerCase();
  return ['fire','water','grass','electric','psychic','normal','dark',
          'fairy','ice','ghost','fighting'].includes(t) ? `type-${t}` : 'type-default';
}

function typeEmoji(type) {
  return TYPE_EMOJI[(type || '').toLowerCase()] || '❓';
}

// ── Add Card Modal ─────────────────────────────────────────────────────────
function openAddModal(pokemonName = '') {
  document.getElementById('add-search-input').value = pokemonName;
  document.getElementById('search-results').innerHTML = '';
  document.getElementById('modal-add').style.display = 'flex';
}

function closeAddModal(e) {
  if (e.target.id === 'modal-add') document.getElementById('modal-add').style.display = 'none';
}

async function searchCards() {
  const name = document.getElementById('add-search-input').value.trim();
  if (!name) return;
  const resultsEl = document.getElementById('search-results');
  resultsEl.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:20px">Buscando...</div>';

  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pokemon_name: name})
  });
  const results = await resp.json();
  resultsEl.innerHTML = '';

  if (!results.length) {
    resultsEl.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:20px">No se encontraron cartas.</div>';
    return;
  }

  const pokemon = allPokemon.find(p => p.name.toLowerCase() === name.toLowerCase());

  for (const r of results) {
    const item = document.createElement('div');
    item.className = 'result-item';
    item.innerHTML = `
      ${r.image_url ? `<img class="result-img" src="${r.image_url}" loading="lazy">` : `<div class="result-img ${typeClass(pokemon?.type_1)}" style="display:flex;align-items:center;justify-content:center;font-size:20px">${typeEmoji(pokemon?.type_1)}</div>`}
      <div class="result-info">
        <div class="result-name">${r.card_name}</div>
        <div class="result-set">${r.set_name} · ${r.rarity}</div>
      </div>
      <div class="result-price">€${r.price.toFixed(2)}</div>`;
    item.onclick = () => addCard(r, pokemon);
    resultsEl.appendChild(item);
  }
}

async function addCard(result, pokemon) {
  if (!pokemon) {
    alert('No se encontró el Pokemon en la lista. Verifica el nombre.');
    return;
  }
  await fetch('/api/cards', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      pokemon_id: pokemon.id,
      card_name: result.card_name,
      set_name: result.set_name,
      rarity: result.rarity,
      price: result.price,
      image_url: result.image_url,
      cardmarket_url: result.cardmarket_url
    })
  });
  document.getElementById('modal-add').style.display = 'none';
  await loadCards();
  renderGrid();
}

// ── Detail Modal ───────────────────────────────────────────────────────────
async function openDetailModal(card) {
  const histResp = await fetch(`/api/cards/${card.id}/history`);
  const history = await histResp.json();
  const pokemon = allPokemon.find(p => p.id === card.pokemon_id);
  const stale = card.price_current == null;

  document.getElementById('detail-content').innerHTML = `
    <div class="detail-layout">
      <div>
        ${card.image_url
          ? `<img class="detail-img" src="${card.image_url}" alt="${card.card_name}" style="cursor:zoom-in" onclick="openLightbox('${largeImage(card.image_url)}')">`
          : `<div class="detail-img ${typeClass(pokemon?.type_1)}" style="aspect-ratio:2.5/3.5;display:flex;align-items:center;justify-content:center;font-size:60px;border-radius:8px">${typeEmoji(pokemon?.type_1)}</div>`}
      </div>
      <div class="detail-meta">
        <div class="detail-pokemon">${card.pokemon_name}</div>
        <div class="detail-card-name">${card.card_name}</div>
        <div class="detail-set">${card.set_name} · ${card.rarity}</div>
        <div class="detail-price ${stale ? 'stale' : ''}">
          ${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}
          ${stale ? ' <span class="badge badge-stale">⚠ precio no actualizado</span>' : ''}
        </div>
        ${buildSparkline(history)}
        <div class="detail-actions">
          <button class="btn-secondary" onclick="toggleStatus(${card.id}, '${card.status}')">
            ${card.status === 'wishlist' ? '✅ Mover a Colección' : '💜 Mover a Wishlist'}
          </button>
          <a href="${card.cardmarket_url}" target="_blank" style="text-decoration:none">
            <button class="btn-secondary" style="width:100%">🔗 Ver en CardMarket</button>
          </a>
          <button class="btn-secondary btn-danger" onclick="deleteCard(${card.id})">🗑 Eliminar</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-detail').style.display = 'flex';
}

function closeDetailModal(e) {
  if (e.target.id === 'modal-detail') document.getElementById('modal-detail').style.display = 'none';
}

// Upgrade a stored thumbnail URL to its high-res version for the lightbox.
function largeImage(url) {
  if (!url) return url;
  if (url.includes('images.scrydex.com')) return url.replace(/\/small$/, '/large');
  if (url.includes('images.pokemontcg.io')) return url.replace(/\.png$/, '_hires.png');
  return url;
}

function openLightbox(url) {
  document.getElementById('lightbox-img').src = url;
  document.getElementById('lightbox').style.display = 'flex';
}

function closeLightbox() {
  document.getElementById('lightbox').style.display = 'none';
}

function buildSparkline(history) {
  if (!history.length) return '';
  const prices = history.map(h => h.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const w = 200, h = 50, pad = 4;
  const points = prices.map((p, i) => {
    const x = pad + (i / Math.max(prices.length - 1, 1)) * (w - pad * 2);
    const y = h - pad - ((p - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  }).join(' ');
  return `
    <div class="sparkline-wrap">
      <div class="sparkline-label">Historial de precio (${history.length} puntos)</div>
      <svg class="sparkline" viewBox="0 0 ${w} ${h}">
        <polyline points="${points}" fill="none" stroke="#7c3aed" stroke-width="1.5"/>
        <circle cx="${points.split(' ').at(-1).split(',')[0]}" cy="${points.split(' ').at(-1).split(',')[1]}" r="3" fill="#c084fc"/>
      </svg>
    </div>`;
}

async function toggleStatus(cardId, currentStatus) {
  const newStatus = currentStatus === 'wishlist' ? 'owned' : 'wishlist';
  await fetch(`/api/cards/${cardId}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: newStatus})
  });
  document.getElementById('modal-detail').style.display = 'none';
  await loadCards();
  renderGrid();
}

async function deleteCard(cardId) {
  if (!confirm('¿Eliminar esta carta?')) return;
  await fetch(`/api/cards/${cardId}`, {method: 'DELETE'});
  document.getElementById('modal-detail').style.display = 'none';
  await loadCards();
  renderGrid();
}

// ── Price Refresh ──────────────────────────────────────────────────────────
async function triggerRefresh() {
  const btn = document.getElementById('btn-refresh');
  btn.classList.add('spinning');
  await fetch('/api/refresh', {method: 'POST'});
  startPolling();
}

// ── Seed Wishlist ──────────────────────────────────────────────────────────
async function triggerSeed() {
  const btn = document.getElementById('btn-seed');
  btn.classList.add('spinning');
  await fetch('/api/seed', {method: 'POST'});
  startPolling();
}

function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    const el = document.getElementById('stat-updated');
    // While seeding, stream newly added cards into the grid.
    if (data.seeding) {
      await loadCards();
      renderGrid();
    }
    if (!data.updating && !data.seeding) {
      clearInterval(pollInterval);
      pollInterval = null;
      document.getElementById('btn-refresh').classList.remove('spinning');
      document.getElementById('btn-seed').classList.remove('spinning');
      el.textContent = data.last_update
        ? 'Actualizado: ' + new Date(data.last_update).toLocaleString('es-ES')
        : '–';
      await loadCards();
      renderGrid();
    }
  }, 5000);
}

// ── Boot ──────────────────────────────────────────────────────────────────
init();
