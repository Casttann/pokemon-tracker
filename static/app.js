// State
let allCards = [];
let allPokemon = [];
let activeTab = 'all';
let activeGen = null;
let activeSort = 'price-desc';
let viewMode = 'pokemon'; // 'pokemon' | 'global' | 'album'
let albumSpread = 0; // índice del par de páginas visible en la vista álbum
let albumOrder = []; // secuencia plana de cartas del álbum (objetos), tal cual la BD
let albumLoaded = false; // ¿ya cargamos el álbum del servidor?
let albumPicker = null; // selección pendiente del selector: {mode, index}
let pollInterval = null;
let planYear = new Date().getFullYear();
let planData = [];

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
  albumLoaded = false; // re-sincroniza el álbum tras añadir/borrar cartas
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
  albumSpread = 0;
  renderGrid();
}

function setSort(value) {
  activeSort = value;
  renderGrid();
}

function setView(btn, mode) {
  document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  viewMode = mode;
  albumSpread = 0;
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
  grid.className = viewMode === 'album' ? 'album-mode' : '';
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

  if (viewMode === 'album') {
    renderAlbum(grid);
    return;
  }

  if (viewMode === 'pokemon') {
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

// ── Album view (secuencia plana editable, persistida en BD) ────────────────
// El álbum es una lista ordenada de cartas. Se rellena 3×3 por página,
// fila a fila. Insertar una carta empuja todas las demás hacia adelante
// (cascada entre filas y páginas). Todo se guarda en BD vía PUT /api/album.
const ALBUM_PER_PAGE = 9; // 3×3

// Orden por defecto la primera vez: por cada Pokémon (orden Pokédex) sus
// mejores 3 cartas (primero las de la colección, luego por precio).
function defaultAlbumOrder() {
  const byPokemon = {};
  for (const c of allCards) (byPokemon[c.pokemon_id] ||= []).push(c);
  const ids = [];
  for (const p of allPokemon) {
    (byPokemon[p.id] || []).slice().sort((a, b) => {
      const ao = a.status === 'owned' ? 0 : 1, bo = b.status === 'owned' ? 0 : 1;
      if (ao !== bo) return ao - bo;
      return (b.price_current || 0) - (a.price_current || 0);
    }).slice(0, 3).forEach(c => ids.push(c.id));
  }
  return ids;
}

async function loadAlbum() {
  const resp = await fetch('/api/album');
  albumOrder = await resp.json();
  albumLoaded = true;
  if (albumOrder.length === 0) {
    const seed = defaultAlbumOrder();
    if (seed.length) await saveAlbumIds(seed);
  }
}

async function saveAlbumIds(ids) {
  const resp = await fetch('/api/album', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order: ids }),
  });
  albumOrder = await resp.json();
  albumLoaded = true;
  renderGrid();
}

function saveAlbum() {
  return saveAlbumIds(albumOrder.map(c => c.id));
}

function renderAlbum(grid) {
  if (!albumLoaded) {
    grid.innerHTML = '<div class="album-loading">Cargando álbum…</div>';
    loadAlbum().then(() => renderGrid());
    return;
  }

  const pages = [];
  for (let i = 0; i < albumOrder.length; i += ALBUM_PER_PAGE) {
    pages.push(albumOrder.slice(i, i + ALBUM_PER_PAGE));
  }
  if (pages.length === 0) pages.push([]);

  const totalSpreads = Math.max(1, Math.ceil(pages.length / 2));
  albumSpread = Math.min(Math.max(0, albumSpread), totalSpreads - 1);

  const left = pages[albumSpread * 2];
  const right = pages[albumSpread * 2 + 1];

  const book = document.createElement('div');
  book.className = 'album-book';

  const prev = document.createElement('button');
  prev.className = 'album-arrow';
  prev.textContent = '‹';
  prev.disabled = albumSpread === 0;
  prev.onclick = () => changeAlbumPage(-1);

  const spread = document.createElement('div');
  spread.className = 'album-spread';
  spread.appendChild(buildAlbumPage(left, albumSpread * 2));
  spread.appendChild(right ? buildAlbumPage(right, albumSpread * 2 + 1) : blankAlbumPage());

  const next = document.createElement('button');
  next.className = 'album-arrow';
  next.textContent = '›';
  next.disabled = albumSpread >= totalSpreads - 1;
  next.onclick = () => changeAlbumPage(1);

  book.appendChild(prev);
  book.appendChild(spread);
  book.appendChild(next);
  grid.appendChild(book);

  const info = document.createElement('div');
  info.className = 'album-nav-info';
  const ownedTotal = albumOrder.filter(c => c.status === 'owned').length;
  info.textContent = `Páginas ${albumSpread * 2 + 1}${right ? '–' + (albumSpread * 2 + 2) : ''}`
    + ` de ${pages.length} · ${ownedTotal}/${albumOrder.length} en colección`;
  grid.appendChild(info);
}

function blankAlbumPage() {
  return Object.assign(document.createElement('section'),
    { className: 'album-page album-page-blank' });
}

function changeAlbumPage(delta) {
  albumSpread += delta;
  renderGrid();
}

function buildAlbumPage(cards, pageIndex) {
  const section = document.createElement('section');
  section.className = 'album-page';
  const startIdx = pageIndex * ALBUM_PER_PAGE;
  const owned = cards.filter(c => c.status === 'owned').length;

  const head = document.createElement('div');
  head.className = 'album-page-head';
  head.innerHTML = `<span class="album-page-title">Página ${pageIndex + 1}</span>
    <span class="album-page-count">${owned}/${cards.length} ✅</span>`;
  section.appendChild(head);

  const sleeve = document.createElement('div');
  sleeve.className = 'album-sleeve';
  for (let i = 0; i < ALBUM_PER_PAGE; i++) {
    const card = cards[i];
    sleeve.appendChild(card
      ? buildAlbumCardSlot(card, startIdx + i)
      : buildAlbumGapSlot(startIdx + i));
  }
  section.appendChild(sleeve);
  return section;
}

// Hueco con carta. Si no es de la colección, se muestra "bloqueado".
// Incluye controles de edición que aparecen al pasar el ratón.
function buildAlbumCardSlot(card, index) {
  const pokemon = allPokemon.find(p => p.id === card.pokemon_id) || {};
  const owned = card.status === 'owned';
  const slot = document.createElement('div');
  slot.className = `album-slot ${owned ? 'owned' : 'wish locked'}`;
  slot.innerHTML = `
    <div class="album-slot-img">
      ${card.image_url
        ? `<img src="${card.image_url}" alt="${card.card_name}" loading="lazy">`
        : `<div class="album-slot-ph ${typeClass(pokemon.type_1)}">${typeEmoji(pokemon.type_1)}</div>`}
      ${owned ? '' : '<span class="album-slot-lock">🔒</span>'}
      <span class="album-slot-badge">${owned ? '✅' : '💜'}</span>
    </div>
    <div class="album-slot-name">${card.card_name}</div>
    <div class="album-slot-price ${card.price_current == null ? 'stale' : ''}">
      ${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}
    </div>`;

  const ctrls = document.createElement('div');
  ctrls.className = 'album-slot-ctrls';
  ctrls.innerHTML = `
    <button title="Variante anterior" data-act="prev">‹</button>
    <button title="Cambiar carta" data-act="change">🔄</button>
    <button title="Insertar carta aquí" data-act="insert">＋</button>
    <button title="Quitar del álbum" data-act="remove">✕</button>
    <button title="Variante siguiente" data-act="next">›</button>`;
  const on = (act, fn) => ctrls.querySelector(`[data-act=${act}]`)
    .addEventListener('click', (e) => { e.stopPropagation(); fn(); });
  on('prev', () => cycleAlbumCard(index, -1));
  on('next', () => cycleAlbumCard(index, 1));
  on('change', () => openAlbumPicker('change', index));
  on('insert', () => openAlbumPicker('insert', index));
  on('remove', () => removeAlbumCard(index));
  slot.appendChild(ctrls);

  slot.onclick = () => openDetailModal(card);
  return slot;
}

// Hueco vacío al final del álbum: invita a insertar una carta ahí.
function buildAlbumGapSlot(index) {
  const slot = document.createElement('div');
  slot.className = 'album-slot gap';
  slot.innerHTML = `<div class="album-gap-plus">＋</div>
    <div class="album-slot-name">Añadir carta</div>`;
  slot.onclick = () => openAlbumPicker('insert', index);
  return slot;
}

// Variantes de la misma especie que NO están ya en el álbum (+ la actual),
// en orden estable para que las flechas ‹ › sean predecibles.
function variantsForSlot(index) {
  const cur = albumOrder[index];
  if (!cur) return [];
  const inAlbum = new Set(albumOrder.map(c => c.id));
  return allCards
    .filter(c => c.pokemon_id === cur.pokemon_id && (c.id === cur.id || !inAlbum.has(c.id)))
    .sort((a, b) => a.id - b.id);
}

function cycleAlbumCard(index, delta) {
  const variants = variantsForSlot(index);
  if (variants.length <= 1) return;
  const curId = albumOrder[index].id;
  let pos = variants.findIndex(c => c.id === curId);
  pos = (pos + delta + variants.length) % variants.length;
  albumOrder[index] = variants[pos];
  saveAlbum();
}

function removeAlbumCard(index) {
  albumOrder.splice(index, 1);
  saveAlbum();
}

// ── Selector de cartas (cambiar/insertar) ──────────────────────────────────
function openAlbumPicker(mode, index) {
  albumPicker = { mode, index };
  const title = mode === 'change' ? 'Cambiar carta del hueco' : 'Insertar carta aquí';
  document.getElementById('picker-title').textContent = title;
  document.getElementById('picker-search').value = '';
  renderAlbumPicker('');
  document.getElementById('modal-picker').style.display = 'flex';
}

function closeAlbumPicker(e) {
  if (!e || e.target.id === 'modal-picker') {
    document.getElementById('modal-picker').style.display = 'none';
    albumPicker = null;
  }
}

function renderAlbumPicker(search) {
  const wrap = document.getElementById('picker-results');
  const inAlbum = new Set(albumOrder.map(c => c.id));
  const q = (search || '').toLowerCase();
  wrap.innerHTML = '';

  for (const p of allPokemon) {
    if (q && !p.name.toLowerCase().includes(q)) continue;
    const cards = allCards.filter(c => c.pokemon_id === p.id);
    if (!cards.length) continue;

    const group = document.createElement('div');
    group.className = 'picker-group';
    group.innerHTML = `<div class="picker-group-head">${p.name}</div>`;
    const row = document.createElement('div');
    row.className = 'picker-row';
    cards.sort((a, b) => (b.price_current || 0) - (a.price_current || 0)).forEach(card => {
      const used = inAlbum.has(card.id);
      const it = document.createElement('div');
      it.className = `picker-item ${used ? 'used' : ''} ${card.status === 'owned' ? 'owned' : ''}`;
      it.innerHTML = `
        ${card.image_url
          ? `<img src="${card.image_url}" loading="lazy" alt="">`
          : `<div class="picker-ph ${typeClass(p.type_1)}">${typeEmoji(p.type_1)}</div>`}
        <div class="picker-item-name">${card.card_name}</div>
        <div class="picker-item-meta">${card.status === 'owned' ? '✅' : '💜'} `
        + `${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}`
        + `${used ? ' · en álbum' : ''}</div>`;
      it.onclick = () => pickAlbumCard(card);
      row.appendChild(it);
    });
    group.appendChild(row);
    wrap.appendChild(group);
  }
  if (!wrap.children.length) wrap.innerHTML = '<div class="picker-empty">Sin resultados</div>';
}

function pickAlbumCard(card) {
  const sel = albumPicker;
  if (!sel) return;
  let index = sel.index;
  // Evita duplicados: si la carta ya estaba en el álbum, la sacamos primero.
  const existing = albumOrder.findIndex(c => c.id === card.id);

  if (sel.mode === 'change') {
    if (existing === index) { closeAlbumPicker(); return; }
    if (existing !== -1) {
      albumOrder.splice(existing, 1);
      if (existing < index) index -= 1;
    }
    if (index < albumOrder.length) albumOrder.splice(index, 1, card);
    else albumOrder.push(card);
  } else { // insert: cascada hacia adelante
    if (existing !== -1) {
      albumOrder.splice(existing, 1);
      if (existing < index) index -= 1;
    }
    if (index > albumOrder.length) index = albumOrder.length;
    albumOrder.splice(index, 0, card);
  }
  closeAlbumPicker();
  saveAlbum();
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

  for (const r of results) {
    // Resolve the Pokemon from the card name itself (e.g. "Blaine's Charmander"
    // -> Charmander), not from the search term, which may not be an exact name.
    const pokemon = findPokemonForCard(r.card_name, name);
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

// Match a card to one of our Pokemon by finding the longest Pokemon name
// contained in the card name; fall back to an exact match on the search term.
function findPokemonForCard(cardName, fallbackName) {
  const cn = (cardName || '').toLowerCase();
  const contained = allPokemon
    .filter(p => cn.includes(p.name.toLowerCase()))
    .sort((a, b) => b.name.length - a.name.length);
  if (contained.length) return contained[0];
  const fb = (fallbackName || '').toLowerCase();
  return allPokemon.find(p => p.name.toLowerCase() === fb);
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

// ── Monthly Planning ───────────────────────────────────────────────────────
const MONTH_NAMES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

// Guía de precios de referencia (€, Todohits + Cardmarket, jun 2026).
// Editable a mano si cambian los precios del mercado.
const PRICE_GUIDE = {
  sobre: 6.5,        // sobre suelto Chaos Rising (Todohits)
  blister: 22,       // blíster 3 sobres + promo (te dio el Charmeleon)
  bundle: 40,        // bundle ~6 sobres
  etb_es: 45,        // ETB español (más barata, menos revalorización)
  etb_en: 85,        // ETB inglés (mantiene/sube valor → tu objetivo)
  box: 200,          // caja 36 sobres
};

// Devuelve un consejo de compra según el dinero disponible ese mes.
// `etbFund` = ahorro acumulado disponible hacia una ETB inglesa.
function buyAdvice(available, etbFund) {
  const g = PRICE_GUIDE;
  if (available <= 0) {
    return 'Presupuesto agotado. Mejor ahorrar hacia la ETB inglesa (~€' + g.etb_en + ').';
  }
  if (available < g.sobre) {
    return 'Casi sin margen: guarda lo que queda hacia la ETB inglesa.';
  }
  if (available >= g.etb_en) {
    return '🎯 Te llega para 1 ETB inglesa (~€' + g.etb_en + ') — la opción que mantiene/sube valor. '
      + 'Sobrante: ' + Math.floor((available - g.etb_en) / g.sobre) + ' sobre(s) suelto(s).';
  }
  // No llega a ETB inglesa este mes: ¿llega sumando ahorro?
  if (etbFund != null && etbFund + available >= g.etb_en) {
    return '💰 Con el ahorro acumulado (€' + etbFund.toFixed(0) + ') + este mes llegas a la ETB inglesa (~€'
      + g.etb_en + '). Recomendado: AHORRAR este mes y comprarla.';
  }
  if (available >= g.bundle) {
    const n = Math.floor(available / g.blister);
    return 'Opciones: ' + n + ' blíster(s) de 3 sobres (€' + g.blister + ' c/u, mejor relación) '
      + 'o un bundle (~€' + g.bundle + '). O guarda hacia la ETB inglesa (~€' + g.etb_en + ').';
  }
  if (available >= g.blister) {
    const sobres = Math.floor((available - g.blister) / g.sobre);
    return '👍 1 blíster de 3 sobres + promo (€' + g.blister + ')'
      + (sobres > 0 ? ' y ' + sobres + ' sobre(s) suelto(s)' : '')
      + '. O ahorra hacia la ETB inglesa.';
  }
  const n = Math.floor(available / g.sobre);
  return n + ' sobre(s) suelto(s) (~€' + g.sobre + ' c/u en Todohits). O acumula hacia la ETB inglesa.';
}

async function openPlanModal() {
  document.getElementById('modal-plan').style.display = 'flex';
  await loadPlan();
}

function closePlanModal(event) {
  if (event && event.target.id !== 'modal-plan') return;
  document.getElementById('modal-plan').style.display = 'none';
}

async function changePlanYear(delta) {
  planYear += delta;
  await loadPlan();
}

async function loadPlan() {
  const resp = await fetch(`/api/plan?year=${planYear}`);
  planData = await resp.json();
  renderPlan();
}

function renderPlan() {
  document.getElementById('plan-year-label').textContent = planYear;
  const totalBudget = planData.reduce((s, m) => s + m.budget, 0);
  const totalSpent = planData.reduce((s, m) => s + m.spent, 0);
  const remaining = totalBudget - totalSpent;
  const now = new Date();
  const curMonth = (planYear === now.getFullYear()) ? now.getMonth() + 1 : 0;

  // Fondo ETB: ahorro no gastado de meses ya pasados/en curso del año.
  const etbFund = planData
    .filter(m => curMonth === 0 || m.month <= curMonth)
    .reduce((s, m) => s + Math.max(0, m.budget - m.spent), 0);

  document.getElementById('plan-summary').innerHTML = `
    <div class="plan-sum-item"><span>Presupuesto anual</span><strong>€${totalBudget.toFixed(2)}</strong></div>
    <div class="plan-sum-item"><span>Gastado</span><strong>€${totalSpent.toFixed(2)}</strong></div>
    <div class="plan-sum-item"><span>Disponible</span><strong class="${remaining < 0 ? 'over' : 'ok'}">€${remaining.toFixed(2)}</strong></div>
  `;

  // Recomendación destacada para el PRÓXIMO mes.
  const nextMonth = (curMonth >= 1 && curMonth <= 11) ? planData[curMonth] : null;
  if (nextMonth) {
    const avail = nextMonth.budget - nextMonth.spent;
    document.getElementById('plan-advice').innerHTML = `
      <div class="plan-advice-label">💡 Próximo mes · ${MONTH_NAMES[nextMonth.month - 1]} (disponible €${avail.toFixed(0)})</div>
      <div class="plan-advice-text">${buyAdvice(avail, etbFund)}</div>`;
  } else {
    document.getElementById('plan-advice').innerHTML = '';
  }

  document.getElementById('plan-months').innerHTML = planData.map(m => {
    const pct = m.budget > 0 ? Math.min(100, (m.spent / m.budget) * 100) : 0;
    const over = m.spent > m.budget;
    const avail = m.budget - m.spent;
    return `
    <div class="plan-month ${m.month === curMonth ? 'current' : ''}">
      <div class="plan-month-head">
        <span class="plan-month-name">${MONTH_NAMES[m.month - 1]}</span>
        <span class="plan-month-bar"><span class="plan-month-fill ${over ? 'over' : ''}" style="width:${pct}%"></span></span>
      </div>
      <div class="plan-month-fields">
        <label>Presupuesto €<input type="number" min="0" step="1" value="${m.budget}" data-m="${m.month}" data-f="budget"></label>
        <label>Gastado €<input type="number" min="0" step="0.01" value="${m.spent}" data-m="${m.month}" data-f="spent"></label>
      </div>
      <div class="plan-month-advice">💡 ${buyAdvice(avail, null)}</div>
      <textarea class="plan-note" placeholder="¿Qué quiero comprar este mes?" data-m="${m.month}" data-f="plan_note">${m.plan_note || ''}</textarea>
      <button class="btn-primary plan-save-btn" onclick="savePlanMonth(${m.month})">Guardar</button>
    </div>`;
  }).join('');
}

async function savePlanMonth(month) {
  const get = (f) => document.querySelector(`#plan-months [data-m="${month}"][data-f="${f}"]`);
  const budget = parseFloat(get('budget').value) || 0;
  const spent = parseFloat(get('spent').value) || 0;
  const plan_note = get('plan_note').value;
  const resp = await fetch('/api/plan', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({year: planYear, month, budget, spent, plan_note})
  });
  planData = await resp.json();
  renderPlan();
}

// ── Dashboard ──────────────────────────────────────────────────────────────
let dashCharts = [];

const GEN_NAMES = {
  0: 'Special', 1: 'Gen 1', 2: 'Gen 2', 3: 'Gen 3', 4: 'Gen 4',
  5: 'Gen 5', 6: 'Gen 6', 7: 'Gen 7', 8: 'Gen 8', 9: 'Gen 9'
};

async function openDashboard() {
  document.getElementById('modal-dashboard').style.display = 'flex';
  const resp = await fetch('/api/stats');
  const stats = await resp.json();
  renderDashboard(stats);
}

function closeDashboard(event) {
  if (event && event.target.id !== 'modal-dashboard') return;
  document.getElementById('modal-dashboard').style.display = 'none';
  dashCharts.forEach(c => c.destroy());
  dashCharts = [];
}

function renderDashboard(stats) {
  const t = stats.totals;
  document.getElementById('dash-kpis').innerHTML = `
    <div class="kpi"><div class="kpi-value">€${t.owned_value.toFixed(2)}</div><div class="kpi-label">Valor colección</div></div>
    <div class="kpi"><div class="kpi-value">${t.owned_count}</div><div class="kpi-label">Cartas en propiedad</div></div>
    <div class="kpi"><div class="kpi-value">€${t.wishlist_value.toFixed(2)}</div><div class="kpi-label">Valor wishlist</div></div>
    <div class="kpi"><div class="kpi-value">${t.wishlist_count}</div><div class="kpi-label">Cartas deseadas</div></div>`;

  dashCharts.forEach(c => c.destroy());
  dashCharts = [];

  const purple = '#7c3aed', light = '#c084fc';
  const tick = '#a99fc7', grid = 'rgba(255,255,255,0.06)';
  const axes = {
    x: { ticks: { color: tick }, grid: { color: grid } },
    y: { ticks: { color: tick }, grid: { color: grid }, beginAtZero: true }
  };

  // Valor en el tiempo
  const vot = stats.value_over_time;
  dashCharts.push(new Chart(document.getElementById('chart-value'), {
    type: 'line',
    data: {
      labels: vot.map(d => d.date),
      datasets: [{
        data: vot.map(d => d.value),
        borderColor: purple, backgroundColor: 'rgba(124,58,237,0.15)',
        fill: true, tension: 0.25, pointRadius: 2, pointBackgroundColor: light
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } }, scales: axes }
  }));

  // Valor por generación
  const gen = stats.by_generation;
  dashCharts.push(new Chart(document.getElementById('chart-gen'), {
    type: 'bar',
    data: {
      labels: gen.map(g => GEN_NAMES[g.generation] || ('Gen ' + g.generation)),
      datasets: [{ data: gen.map(g => g.value), backgroundColor: purple }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } }, scales: axes }
  }));

  // Cartas por rareza
  const rar = stats.by_rarity;
  const palette = ['#7c3aed', '#c084fc', '#a855f7', '#9333ea', '#d8b4fe',
    '#6d28d9', '#8b5cf6', '#e9d5ff'];
  dashCharts.push(new Chart(document.getElementById('chart-rarity'), {
    type: 'doughnut',
    data: {
      labels: rar.map(r => r.rarity),
      datasets: [{ data: rar.map(r => r.count),
        backgroundColor: rar.map((_, i) => palette[i % palette.length]) }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: tick, font: { size: 10 } } } } }
  }));

  // Top movers
  const movers = stats.top_movers;
  document.getElementById('dash-movers').innerHTML = movers.length ? `
    <div class="dash-chart-title">Mayores movimientos de precio</div>
    <table class="movers-table">
      <thead><tr><th>Carta</th><th>Set</th><th>Inicial</th><th>Actual</th><th>Cambio</th></tr></thead>
      <tbody>${movers.map(m => `
        <tr>
          <td>${m.card_name}</td>
          <td>${m.set_name}</td>
          <td>€${m.first_price.toFixed(2)}</td>
          <td>€${m.latest_price.toFixed(2)}</td>
          <td class="${m.change_pct >= 0 ? 'mover-up' : 'mover-down'}">${m.change_pct >= 0 ? '▲' : '▼'} ${Math.abs(m.change_pct).toFixed(1)}%</td>
        </tr>`).join('')}</tbody>
    </table>` : '<div class="dash-chart-title">Sin suficiente histórico para calcular movimientos.</div>';
}

// ── Boot ──────────────────────────────────────────────────────────────────
init();
