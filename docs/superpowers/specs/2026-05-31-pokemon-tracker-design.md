# Pokemon Card Collection Tracker — Design Spec

**Date:** 2026-05-31  
**Status:** Approved  

---

## Overview

A personal desktop app (Mac) to track a Pokemon card collection focused on starter Pokemon from all generations (Gen 1–9), plus Pikachu and Eevee with all their evolutions. Cards are in English. The app launches a local Flask server and opens automatically in the browser.

**Goal:** See the full collection at a glance — which cards are owned, which are on the wishlist, and their current market price from CardMarket.

---

## Pokemon Scope

88 Pokemon total across the following groups:

- **Gen 1:** Bulbasaur, Ivysaur, Venusaur, Charmander, Charmeleon, Charizard, Squirtle, Wartortle, Blastoise
- **Gen 2:** Chikorita, Bayleef, Meganium, Cyndaquil, Quilava, Typhlosion, Totodile, Croconaw, Feraligatr
- **Gen 3:** Treecko, Grovyle, Sceptile, Torchic, Combusken, Blaziken, Mudkip, Marshtomp, Swampert
- **Gen 4:** Turtwig, Grotle, Torterra, Chimchar, Monferno, Infernape, Piplup, Prinplup, Empoleon
- **Gen 5:** Snivy, Servine, Serperior, Tepig, Pignite, Emboar, Oshawott, Dewott, Samurott
- **Gen 6:** Chespin, Quilladin, Chesnaught, Fennekin, Braixen, Delphox, Froakie, Frogadier, Greninja
- **Gen 7:** Rowlet, Dartrix, Decidueye, Litten, Torracat, Incineroar, Popplio, Brionne, Primarina
- **Gen 8:** Grookey, Thwackey, Rillaboom, Scorbunny, Raboot, Cinderace, Sobble, Drizzile, Inteleon
- **Gen 9:** Sprigatito, Floragato, Meowscarada, Fuecoco, Crocalor, Skeledirge, Quaxly, Quaxwell, Quaquaval
- **Special:** Pikachu, Raichu, Eevee, Vaporeon, Jolteon, Flareon, Espeon, Umbreon, Leafeon, Glaceon, Sylveon

In the `pokemon` table, the "Special" group is stored with `generation = 0`. In the UI, generation 0 maps to the filter label "Special". This mapping is hard-coded in the frontend filter logic.

---

## Architecture

**Stack:** Python 3.11+ / Flask / SQLite (via SQLAlchemy) / APScheduler / BeautifulSoup4 / Requests / HTML + CSS + Vanilla JS

**Project structure:**
```
Pokemon Tracker/
├── app.py               # Flask app, routes
├── database.py          # SQLAlchemy models and DB init
├── scraper.py           # CardMarket price scraper
├── image_lookup.py      # PokemonTCG API image resolver
├── scheduler.py         # Daily auto-update via APScheduler
├── pokemon_data.py      # Static list of 88 Pokemon (seed data)
├── run.sh               # Launch script (starts Flask, opens browser)
├── requirements.txt
├── templates/
│   └── index.html       # Single-page app template
├── static/
│   ├── style.css
│   └── app.js
└── docs/
    └── superpowers/specs/
```

**Data storage:** SQLite at `~/.pokemon_tracker/tracker.db` so data persists across app updates.

---

## Data Models

### Table: `pokemon`
Seeded once at startup. Never modified by the user.

| Column       | Type    | Notes                                                    |
|--------------|---------|----------------------------------------------------------|
| id           | INTEGER | Primary key                                              |
| name         | TEXT    | English name (e.g. "Charizard")                          |
| generation   | INTEGER | 1–9 for starter generations; 0 for the Special group (Pikachu/Eevee lines) |
| type_1       | TEXT    | Primary type                                             |
| type_2       | TEXT    | Secondary type (nullable)                                |

### Table: `cards`
One row per card the user has added to wishlist or collection.

| Column          | Type    | Notes                                                                 |
|-----------------|---------|-----------------------------------------------------------------------|
| id              | INTEGER | Primary key                                                           |
| pokemon_id      | INTEGER | FK → pokemon.id                                                       |
| card_name       | TEXT    | Full card name (e.g. "Charizard ex - 199")                            |
| set_name        | TEXT    | Set name (e.g. "Obsidian Flames")                                     |
| rarity          | TEXT    | e.g. "Special Illustration Rare"                                      |
| image_url       | TEXT    | URL to card image (from PokemonTCG API lookup at add-time; see Image Sourcing). Trusted as-is — no URL validation beyond nullability check. |
| price_current   | REAL    | Latest price in EUR from CardMarket (null if never fetched)           |
| price_updated   | TEXT    | ISO datetime of last successful price update (null if never updated)  |
| status          | TEXT    | "wishlist" or "owned"                                                 |
| cardmarket_url  | TEXT    | Direct link to the card on CardMarket (validated at save time)        |

**Uniqueness:** No unique constraint on `(pokemon_id, cardmarket_url)`. The same card can be added multiple times (e.g. two copies). This is intentional — the user may want to track multiple copies or compare prices of the same card from different listings.

`budget_limit` is **not** stored in the database — the €100 cap is a hard-coded application constant (`MAX_PRICE = 100.0`) applied in the search route and scraper result filtering.

### Table: `price_history`
Append-only log of price snapshots.

| Column    | Type    | Notes              |
|-----------|---------|--------------------|
| id        | INTEGER | Primary key        |
| card_id   | INTEGER | FK → cards.id      |
| price     | REAL    | Price in EUR       |
| recorded  | TEXT    | ISO datetime       |

A snapshot is written to `price_history` both when a card is first added (using the search result price) and on every subsequent price update. This ensures the sparkline always has at least one data point.

---

## Modules

### `pokemon_data.py`
Static Python list of all 88 Pokemon with name, generation, and type. Loaded at DB init to seed the `pokemon` table. No network calls.

### `database.py`
- SQLAlchemy models for all three tables
- `init_db()`: creates tables and seeds `pokemon` if empty
- Helper functions: `get_all_cards()`, `get_card_by_id()`, `add_card()`, `update_card_status()`, `delete_card()`, `save_price_snapshot()`

### `scraper.py`
- `search_cardmarket(pokemon_name: str, max_price: float = 100.0) -> list[dict]`: searches CardMarket for English cards of a given Pokemon. Returns top results filtered to `price <= max_price`. Each result includes: `card_name`, `set_name`, `rarity`, `price` (float, EUR), `cardmarket_url`. Budget filtering happens here, server-side.
- `update_price(cardmarket_url: str) -> float | None`: fetches the current price for a card from its stored CardMarket URL. Returns `None` on failure.
- Uses random delays (1–3s between requests) and realistic browser `User-Agent` headers to reduce blocking risk.
- On failure (block, timeout, parse error): returns `None`; the caller keeps the last known price unchanged.

### `image_lookup.py`
- `find_card_image(card_name: str, set_name: str) -> str | None`: queries the [PokemonTCG API](https://pokemontcg.io/) (free, no auth required for basic use) by card name and set name. Returns the `images.large` URL from the first matching result, or `None` if not found.
- Called once at add-time when saving a card. The resolved URL is stored in `cards.image_url`. Not called again unless the image is missing.
- If no match is found, `image_url` is stored as `None` and the frontend renders a type-colored placeholder SVG.

### `scheduler.py`
- Uses APScheduler's `BackgroundScheduler`
- Job runs daily at 09:00 local time
- Iterates all cards. Cards where `cardmarket_url` is null are silently skipped. For cards with a URL, calls `scraper.update_price()` and saves to `price_history` on success.
- Writes ISO timestamp to `~/.pokemon_tracker/last_update.txt` after each full run
- On Flask startup: if `last_update.txt` is missing or its timestamp is >24h ago, triggers an immediate background update run

### `app.py`
Flask routes:

| Method | Route                        | Action                                                                                     |
|--------|------------------------------|--------------------------------------------------------------------------------------------|
| GET    | `/`                          | Render main page                                                                           |
| GET    | `/api/cards`                 | Return all cards (JSON). Supports `?status=wishlist\|owned` filter                         |
| GET    | `/api/pokemon`               | Return full Pokemon list (88 entries) with card count per Pokemon                          |
| POST   | `/api/cards`                 | Add a card. Body: `{pokemon_id, cardmarket_url, card_name, set_name, rarity, price, image_url}`. `price` is the float value from the search result (user-supplied; must be a positive number ≤ 100.0, else HTTP 400). `image_url` is passed directly from the search result (already resolved by `/api/search`); if null, stored as null. Validates that `cardmarket_url` starts with `https://www.cardmarket.com/` (else HTTP 400). Saves initial price snapshot to `price_history`. Saves as status `"wishlist"`. |
| PATCH  | `/api/cards/<id>`            | Update `status` field only. Body: `{"status": "owned" \| "wishlist"}`. Returns updated card JSON on success, HTTP 400 if value is invalid, HTTP 404 if card not found. |
| DELETE | `/api/cards/<id>`            | Remove card and its price history. Cascade is handled at application level in `database.py` (`delete_card()` deletes `price_history` rows first, then the card). Returns HTTP 204 on success. |
| GET    | `/api/cards/<id>/history`    | Return price history for a card as `[{price, recorded}]` sorted by date ascending         |
| POST   | `/api/search`                | Search CardMarket. Body: `{pokemon_name}`. Calls `scraper.search_cardmarket(pokemon_name, max_price=100.0)`, then for each result calls `image_lookup.find_card_image(card_name, set_name)` and appends `image_url` to the result dict (null if not found). Returns the enriched list. |
| POST   | `/api/refresh`               | Trigger an immediate background price update for all cards. Returns `{status: "started"}`. |
| GET    | `/api/status`                | Returns `{last_update: "<ISO datetime or null>", updating: <bool>}`                       |

### Launch (`run.sh`)
1. Activates virtual environment (`venv/`)
2. Finds a free port starting from 5000 (tries 5000–5010; exits with error if all taken)
3. Starts Flask with `FLASK_PORT=<port> python app.py` in background
4. `app.py` reads the port from `os.environ.get("FLASK_PORT", "5000")` and passes it to `app.run(port=int(port))`
5. Waits up to 5s for the port to accept connections (polls with `nc -z localhost <port>`)
6. Opens `http://localhost:<port>` in the default browser using `open`

---

## Frontend

Single HTML page (`index.html`) with CSS + vanilla JS. No build step, no npm.

**Header:**
- App title "Pokédex Tracker"
- Stats bar: total cards | wishlist value (€) | collection value (€) | last updated (from `/api/status`)
  - All stats are computed client-side from the full card list returned by `GET /api/cards` (no filter applied — fetch all, compute locally).
  - Wishlist value = sum of `price_current` for all cards with `status = "wishlist"` where `price_current` is not null. Cards with null price are excluded from the total (not counted as 0).
  - Collection value = same calculation for `status = "owned"`.
- "Actualizar precios" button → calls `POST /api/refresh`, then polls `GET /api/status` every 5 seconds while `updating: true`. When `updating` becomes `false`, stops polling, refreshes the card list via `GET /api/cards`, and updates the stats bar.

**Filter bar:**
- Tabs: All / Wishlist / Owned
- Generation filter: All / Gen 1 / Gen 2 / … / Gen 9 / Special (Special = `generation === 0`)
- Search input (client-side filter on Pokemon name)

**Main grid:**
- All 88 Pokemon slots are always shown so the user can see at a glance what is missing.
- Each Pokemon slot that has **one card** shows a single tile: card image, Pokemon name, card name, price badge, status badge (Wishlist 💜 / Owned ✅).
- Each Pokemon slot that has **multiple cards** shows a stacked tile (visual stack effect). Clicking it expands to show all individual cards for that Pokemon in a small sub-grid within the slot, each with its own image, name, price, and status badge.
- Pokemon with no cards yet show a grey "empty slot" tile — clicking it opens the Add Card modal pre-filled with that Pokemon's name.

**Add Card modal:**
- Search field (pre-filled with Pokemon name, editable)
- "Buscar" button → calls `POST /api/search`
- Results list: card image (from PokemonTCG API, returned in search results), name, set, rarity, price
- Click a result → calls `POST /api/cards` → card saved as Wishlist → modal closes → grid updates

**Card detail modal (click on existing card):**
- Large card image (or placeholder if `image_url` is null)
- Full name, set, rarity
- Price current + sparkline (SVG line chart of `price_history`; if only 1 data point, show a flat line with a dot — no "no data" error)
- Button: "Mover a Colección" or "Mover a Wishlist" (calls `PATCH /api/cards/<id>`)
- Button: "Ver en CardMarket" (opens `cardmarket_url` in new tab)
- Button: "Eliminar" (confirm dialog → calls `DELETE /api/cards/<id>`)

**Visual style:**
- Background: `#0a0a0f`
- Card backgrounds: `#0f0f1a`
- Borders: `#312e81`
- Accent: `#c084fc` (purple)
- Text: `#e2e8f0`
- Price: `#c084fc`
- Owned badge: `#4ade80` (green)
- Wishlist badge: `#c084fc` (purple)
- Font: System font stack (no Google Fonts dependency)

---

## Image Sourcing

Card images come from the [PokemonTCG API](https://pokemontcg.io/) (free, no API key required for basic requests, rate limit ~1000 req/day). The lookup is done at search time (inside `POST /api/search`) using `card_name` + `set_name` as search terms against the PokemonTCG API. The resolved `images.large` URL is included in the search response and passed by the client when saving a card via `POST /api/cards`. It is stored in `cards.image_url` and never re-fetched.

**Caching during search:** To avoid hitting the PokemonTCG API rate limit, `image_lookup.find_card_image()` uses an in-memory dict cache keyed by `(card_name, set_name)` that persists for the lifetime of the Flask process. Repeated searches for the same card do not trigger extra API calls.

**Rate limit during search:** `POST /api/search` enriches each result with an image lookup. If the PokemonTCG API returns an HTTP 429 (rate limited) mid-batch, `find_card_image()` returns `None` for that result and all subsequent ones in the same batch. The search still returns results — images are just null for the rate-limited ones. The user can still add the card and the image will be null in the DB.

If the PokemonTCG API returns no match, `image_url` is `null` and the frontend renders a colored SVG placeholder based on the Pokemon's `type_1`.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| CardMarket scrape blocked or timeout | `update_price()` returns `None`; last known price unchanged; card shows "⚠ precio no actualizado" badge |
| Card image not found in PokemonTCG API | `image_url` stored as `null`; frontend shows type-colored SVG placeholder |
| Flask port 5000–5010 all in use | `run.sh` exits with error message: "No free port found (5000-5010)" |
| DB file missing at startup | `init_db()` re-creates it (data loss accepted for personal tool) |
| Search returns price >€100 | `scraper.search_cardmarket()` filters these out before returning results |
| `cardmarket_url` fails validation in `POST /api/cards` | Returns HTTP 400 with message "URL must start with https://www.cardmarket.com/" |
| Price history empty (new card) | First snapshot written at add-time; sparkline always has ≥1 data point |
| `/api/refresh` called while update already running | Returns `{status: "already_running"}` immediately, no duplicate job started |

---

## Out of Scope

- Cloud sync or multi-device
- User authentication
- Mobile support
- Tracking non-starter / non-Pikachu / non-Eevee Pokemon
- Cards in languages other than English
- Cards priced above €100 (filtered out at search time)
- Windows or Linux support
- Card condition / grading tracking (e.g. NM, LP, PSA grade)
- Editing a saved card's `card_name`, `set_name`, or `cardmarket_url` — to correct a wrong card, delete it and re-add
