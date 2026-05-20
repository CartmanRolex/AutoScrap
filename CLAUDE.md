# AutoScrap — Swiss Car Listing Scraper

## Goal
Scrape new listings from https://www.autoscout24.ch/fr/s every 2 minutes
and store them incrementally in a local SQLite database.

## Stack
- Python 3.13 + patchright (patched Playwright fork for Cloudflare bypass)
- sqlite3 (stdlib) for the database

## Phases
- Phase 1 (discover.py): stealth browser navigates the site, intercepts all XHR/Fetch
  JSON responses, dumps to data/api_discovery.jsonl + data/trace.har
- Phase 2 (main.py): calls the discovered API endpoint inside the same browser session
  (keeps CF cookies alive), polls every 120s, upserts new listings into autoscrap.db

## Dev Workflow
1. Activate venv: `.venv\Scripts\activate`
2. After every meaningful change: git add → git commit → git push
3. Never commit: .venv/, data/*.db, data/*.jsonl, data/*.har

## Git Remote
git@github-autoscrap:CartmanRolex/AutoScrap.git

---

## Phase 1 Findings — API & Data Format

### Cloudflare bypass
patchright (v1.59.1) passes CF Managed Challenge automatically in non-headless mode.
No additional config needed — just launch with `headless=False`.

### Data source
Listings are **not** fetched via XHR/API calls. They are embedded in the SSR HTML as a
single `<script type="application/ld+json" data-testid="structured-schema-srp">` block.
The block is a schema.org `Organization` object whose `mainEntity.offers.itemListElement`
array contains one entry per listing. Each entry has an `offers` object (price, URL, seller)
with an `itemOffered` of type `Car`.

### JSON-LD path to listings
```
root                              (Organization)
  .mainEntity                     (ItemList or similar)
    .offers
      .itemListElement[i]
        .offers                   (Offer)
          .priceCurrency          "CHF"
          .price                  65900
          .url                    "https://www.autoscout24.ch/fr/d/bmw-...-20478974"
          .availability           "https://schema.org/InStock"
          .seller                 (AutoDealer or Person)
            .name, .address.addressLocality, .address.postalCode
          .itemOffered            (Car)
            .name                 "BMW 540d xDrive 48V Touring M Sport Pro AHK 4x4"
            .brand.name           "BMW"
            .model                "540"
            .vehicleTransmission  "Automatique"
            .mileageFromOdometer.value  14500
            .vehicleEngine.enginePower.value  303
            .vehicleEngine.fuelType     "Hybride léger diesel/électrique"
            .image                "https://listing-images.autoscout24.ch/..."
```

### Listing ID extraction
The listing ID is the last segment of the URL, e.g. `20478974` from
`https://www.autoscout24.ch/fr/d/bmw-...-20478974`.

### Fields available
| Field | Source | Notes |
|---|---|---|
| price_chf | offers.price | integer CHF |
| url | offers.url | contains listing ID |
| seller_name | offers.seller.name | |
| seller_type | offers.seller.@type | AutoDealer / Person |
| seller_city | offers.seller.address.addressLocality | |
| car_name | itemOffered.name | full title |
| car_brand | itemOffered.brand.name | |
| car_model | itemOffered.model | |
| car_transmission | itemOffered.vehicleTransmission | |
| car_km | itemOffered.mileageFromOdometer.value | |
| car_power_hp | itemOffered.vehicleEngine.enginePower.value | |
| car_fuel | itemOffered.vehicleEngine.fuelType | |
| car_image | itemOffered.image | |
| car_year | itemOffered.modelDate | often null in listing view |
| car_body | itemOffered.bodyType | often null in listing view |

### Scraping strategy (Phase 2)
1. Keep the patchright browser session alive (CF cookies stay valid).
2. Every 120s: navigate to `https://www.autoscout24.ch/fr/s` (or call `page.reload()`).
3. Extract the JSON-LD block with `re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)`.
4. Parse → extract `mainEntity.offers.itemListElement[*].offers`.
5. Derive listing ID from URL tail.
6. Upsert into SQLite (dedup by ID).

### Pagination
The listing page shows ~20 results. To get more, append `?page=2` etc. or use filters.
For incremental tracking, page 1 sorted by newest is sufficient (sort param TBD).

### Sort URL
`?sort=createdDate&dir=desc` — confirmed working. Key: "Ajoutés récemment".
`desc=true` does NOT work (returns CF challenge). `dir=desc` is the correct param.

### Cloudflare warm-up required
Navigating directly to the sorted URL on a fresh browser session triggers CF challenge.
Fix: always navigate to the BASE URL first (unsorted), then navigate to the sorted URL.
The `navigate_to_listings()` function in `scraper/fetcher.py` handles this automatically.
Subsequent `reload_listings()` calls reuse the live session and work fine.
