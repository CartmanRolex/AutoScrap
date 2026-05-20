# AutoScrap — Handoff Notes

## Project State (as of 2026-05-20)

Full scraper for autoscout24.ch is working and live.
anibis.ch is now implemented and runs alongside autoscout24.ch in `main.py`.

---

## autoscout24.ch — COMPLETE & WORKING

### How it works
- `python main.py` — opens Chrome (patchright), polls every 120s, stores in SQLite
- `python verify_sort.py` — quick one-shot test
- `python export_json.py` — dump DB to data/listings_export.json

### Cloudflare bypass
- Uses `patchright` (patched Chromium, not standard Playwright)
- CF shows an interactive Turnstile checkbox on first load
- Auto-bypassed by: simulating mouse movement across the page, then clicking the
  iframe checkbox at absolute coordinates using `page.mouse.click(tx, ty)`
- Code: `scraper/fetcher.py` → `_human_mouse()` + `_auto_pass_cf()`
- CF cookies persist for the session; subsequent reloads don't re-trigger challenge

### Sort URL (CORRECT — verified by user)
```
https://www.autoscout24.ch/fr/s?sort%5B0%5D%5Btype%5D=CREATED_DATE&sort%5B0%5D%5Border%5D=DESC
```
Decoded: `?sort[0][type]=CREATED_DATE&sort[0][order]=DESC`
Previous attempts (`?sort=createdDate&dir=desc` etc.) did NOT work.

### Data extraction
- Data is NOT in XHR calls — it is SSR-embedded in the HTML
- Embedded inside `<script>self.__next_f.push([1, "..."])</script>` (Next.js App Router streaming)
- Key: look for `\"prefetchedListings\":` in the raw HTML string
- The JSON is double-escaped: `\"key\"` → unescape with `.replace('\\"', '"').replace('\\\\', '\\')`
  DO NOT do `.replace('\\n', '\n')` — that breaks JSON parsing (newlines in teasers)
- 20 listings per page, `content[]` array

### Fields per listing (autoscout24)
All stored in `data/autoscrap.db`, table `listings`:
- id, url, version_full_name, condition_type, vehicle_category
- make_id, make_name, make_key, model_id, model_name, model_key
- horse_power, kilo_watts, fuel_type, transmission_type, transmission_type_group
- mileage, range_km, consumption_combined
- first_registration_date, first_registration_year
- had_accident, inspected, has_additional_tires, has_new_tires
- price_chf, previous_price_chf, leasing_monthly_chf
- seller_id, seller_name, seller_type, seller_city, seller_zip
- warranty_type, teaser
- as24_created_at, as24_modified_at
- first_seen_at, last_seen_at, is_active
- raw_json (full blob for future-proofing)

### DB currently has ~67 listings (growing with each poll)

---

## anibis.ch — IMPLEMENTED

### Key facts
- URL: `https://www.anibis.ch/fr/q/voitures/Ak8CkY2Fyc5TAwMDA?sorting=newest&page=1`
- **NO Cloudflare challenge** — plain `httpx` GET works, NO browser needed
- **30 listings per page**, ~78,802 total listings
- robots.txt: `/q/` paths are allowed
- DB primary keys are source-prefixed (`anibis:{listingID}`) to avoid collisions with AutoScout24 IDs

### Two-step fetch strategy (important!)
The search page gives minimal data. The detail page has full structured data.

#### Step 1 — Search page
GET `https://www.anibis.ch/fr/q/voitures/Ak8CkY2Fyc5TAwMDA?sorting=newest&page=1`
Data in: `__NEXT_DATA__` script tag (standard Next.js)
Path: `props.pageProps.dehydratedState.queries[0].state.data.listings.edges[i].node`

Fields available on search page:
- `listingID` — unique string ID
- `title` — free text (e.g. "VW Polo 1.0 TSI Comfortline")
- `body` — full description text
- `formattedPrice` — string "10 900.-" → parse to int: remove spaces + ".-"
- `timestamp` — ISO 8601 (when listed)
- `highlighted` — boolean (promoted listing)
- `postcodeInformation.postcode`, `.locationName`, `.canton.shortName`, `.canton.name`
- `sellerInfo.alias` — seller username
- `sellerInfo.subscriptionInfo.subscriptionBadge` — if present → professional seller
- `images` — array of `{__typename: "ListingImage"}` (NO URLs on search page)
- `thumbnail.normalRendition.src` — thumbnail URL (available on search page)
- `thumbnail.retinaRendition.src` — retina thumbnail URL
- `seoInformation.frSlug` — e.g. `vaud/vehicules/voitures/vw-polo-1-0-tsi-comfortline-offre-exceptionnelle`
- `formattedSource` — null for direct listings

#### Step 2 — Detail page (fetch for new listings only)
URL pattern: `https://www.anibis.ch/fr/vi/{frSlug}/{listingID}`
Example: `https://www.anibis.ch/fr/vi/vaud/vehicules/voitures/vw-polo-1-0-tsi-comfortline-offre-exceptionnelle/54548777`

Data in: `__NEXT_DATA__`
Path: `props.pageProps.dehydratedState.queries[0].state.data.listing` (singular)

Extra fields on detail page:
- `properties[]` array — key-value vehicle attributes:
  - `cars_carAutoScoutBrand` → make (e.g. "VW")
  - `cars_carAutoScoutModel` → model (e.g. "POLO")
  - `cars_carAutoScoutRegistrationYear` → year (e.g. "2019")
  - `cars_carAutoScoutMileage` → mileage km (e.g. "89271")
  - `cars_carAutoScoutBodyType` → body type (e.g. "Petite voiture")
  - `cars_carAutoScoutDoors` → doors (e.g. "5")
  - `cars_carAutoScoutColor` → color (e.g. "Gris")
  - `cars_carAutoScoutFuelType` → fuel (e.g. "Essence")
  - `cars_carAutoScoutTransmissionType` → transmission (e.g. "Manuelle")
  - `cars_carAutoScoutHorsepower` → HP (e.g. "95")
- `images[]` with full rendition URLs (normalRendition.src, retinaRendition.src per image)
- `coordinates` — `{latitude: float, longitude: float}`
- `language` — "FR"
- `address` — full address if provided
- `phoneInfo` — phone number if provided

Note: anibis pulls car specs from autoscout24's database (hence `cars_carAutoScout*` prefix).

### DB changes implemented
Add these columns to the existing `listings` table:
```sql
ALTER TABLE listings ADD COLUMN source TEXT NOT NULL DEFAULT 'autoscout24';
ALTER TABLE listings ADD COLUMN body_type TEXT;
ALTER TABLE listings ADD COLUMN color TEXT;
ALTER TABLE listings ADD COLUMN doors INTEGER;
ALTER TABLE listings ADD COLUMN latitude REAL;
ALTER TABLE listings ADD COLUMN longitude REAL;
```
Also rename/repurpose `teaser` for anibis `body` description text.
Add index: `CREATE INDEX IF NOT EXISTS idx_source ON listings(source);`

### anibis parser logic
```python
# Price parsing
price = int(node["formattedPrice"].replace(" ", "").replace(".-","").replace("'",""))

# URL construction
url = f"https://www.anibis.ch/fr/vi/{node['seoInformation']['frSlug']}/{node['listingID']}"

# Properties extraction from detail page
props = {p["listingPropertyID"]: p["formattedValue"]
         for p in detail["properties"]}
make = props.get("cars_carAutoScoutBrand")
model = props.get("cars_carAutoScoutModel")
year = int(props.get("cars_carAutoScoutRegistrationYear", 0)) or None
mileage = int(props.get("cars_carAutoScoutMileage", 0)) or None
# etc.

# Seller type
is_pro = bool(node.get("sellerInfo", {}).get("subscriptionInfo"))
seller_type = "professional" if is_pro else "private"

# source field
source = "anibis"
```

### Recommended polling strategy
- Poll search page every 120s → get 30 IDs
- Check which IDs are NOT already in DB
- For each new ID: fetch detail page → parse → upsert (source="anibis")
- For existing IDs: just update last_seen_at (no detail fetch needed)
- Warm polls = 1 HTTP request total; cold polls = up to 31 requests

### Files created
- `scraper/anibis_fetcher.py` — httpx-based, no browser
- `scraper/anibis_parser.py` — parse search node + detail page __NEXT_DATA__
- `verify_anibis.py` — quick one-shot test for Anibis

### Files modified
- `db/schema.py` — add columns + migration (ALTER TABLE for existing DB)
- `db/repository.py` — ensure upsert handles new columns
- `main.py` — add anibis poll coroutine alongside autoscout24 loop
- `requirements.txt` — add `httpx`

### httpx installation
```
.venv\Scripts\pip install httpx
```

---

## Project Structure
```
AutoScrap/
├── CLAUDE.md              — project goals, findings, dev workflow
├── HANDOFF.md             — this file
├── requirements.txt
├── main.py                — polling loop for autoscout24 + anibis
├── verify_sort.py         — quick test for autoscout24
├── verify_anibis.py       — quick test for anibis
├── test_parse.py          — test extraction from HTML dump
├── find_sort_url.py       — helper to discover sort URL via browser click
├── export_json.py         — dump DB to JSON
├── discover.py            — Phase 1 exploration script (kept for reference)
├── scraper/
│   ├── browser.py         — patchright launch, user-agent
│   ├── fetcher.py         — autoscout24 fetch + CF bypass + extraction
│   ├── parser.py          — autoscout24 listing → DB row
│   ├── anibis_fetcher.py  — anibis HTTP fetches
│   └── anibis_parser.py   — anibis search/detail → DB row
├── db/
│   ├── schema.py          — SQLite DDL + init_db()
│   └── repository.py      — upsert_listing(), count_listings()
└── data/
    ├── autoscrap.db       — live SQLite database
    └── listings_export.json — last JSON export
```

## Git remote
`git@github-autoscrap:CartmanRolex/AutoScrap.git`
SSH key: `~/.ssh/id_ed25519_autoscrap`
SSH config host alias: `github-autoscrap`

## Always commit + push after every meaningful change
```
git add <files>
git commit -m "feat/fix/refactor: description"
git push
```
