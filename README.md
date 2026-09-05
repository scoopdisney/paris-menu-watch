# paris-menu-watch

Daily menu watch for Disneyland Paris (Disneyland Park, Disney Adventure World, Disney Village, the Disney hotels, Golf Disneyland), from Disney's official site disneylandparis.com. Separate from `disney-menu-watch`, `wdw-menu-watch`, `tokyo-menu-watch` and `shanghai-menu-watch`.

**How it works.** Disney publishes each restaurant's menu as a PDF on `media.disneylandparis.com`, linked from `/en-gb/dining/<location>/<venue>`. The site sits behind a Queue-it gate; the scanner carries the pass in a cookie jar. 83 of 84 PDFs are real text with euro prices (Earl of Sandwich is image-only and is tracked by bytes). Same two-level design as Shanghai:

- **Reliable — the alert.** Per venue: new PDF filename, changed bytes, changed set of prices (with the exact euro amounts added and removed), added/removed text lines, page-count change, venue added or removed, PDF removed from the page. Changed PDFs are rendered to JPEG page images under `data/renders/` and linked from the issue comment.
- **Best-effort — the log.** `data/prices.csv` lists every euro price token with a guessed item name (Pulled, Venue, Location, PdfFile, Page, PriceEUR, ItemGuess, Slug). Prices are exact; names are heuristic and bilingual.

**Bandwidth.** The 82 PDFs total about 1.1GB, so every run HEADs each PDF first and only downloads the ones whose ETag changed. A quiet run moves ~50MB; the first run and a menu-change day move more.

**How it runs.** Every 3 hours from 8am Paris time: sitemap index → dining URLs (the per-location `/map` pages are excluded — they link every PDF) → each venue page → HEAD/GET each PDF → diff against `data/venues.csv` and `data/text/` → commit → one summary per day on the `daily-log` issue, plus an immediate comment when anything changed. Transient page 404s (the gate hiccups) carry the committed rows forward silently instead of reporting a venue as gone.

**Files.** `data/venues.csv` (Pulled, Slug, Venue, Location, PdfUrl, PdfFile, Meta, Sha, Bytes, Pages, PriceCount, Prices, LastChanged), `data/prices.csv`, `data/text/`, `data/renders/`, `data/last-daily.txt`.

**Coverage as of 2026-09-05.** 87 dining pages in Disney's sitemap, 80 with a menu PDF (82 PDFs), ~2,030 euro price tokens. Third-party Disney Village tenants (McDonald's, Starbucks, Rosalie, The Royal Pub) publish no PDF and are tracked for presence only.

**Tuning.** `RENDER_DPI` (default 70) and `MAX_RENDER_PAGES` (default 8).
