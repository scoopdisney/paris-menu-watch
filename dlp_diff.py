"""Snapshot comparison for paris-menu-watch: per-venue PDF change detection, rows, events."""
import os
from collections import Counter

from menu_pdf import is_latin
from dlp_report import describe_change
from dlp_util import read_csv

VEN_HEADER = ['Pulled', 'Slug', 'Venue', 'Location', 'PdfUrl', 'PdfFile', 'Meta', 'Sha', 'Bytes', 'Pages', 'PriceCount', 'Prices', 'LastChanged']
PR_HEADER = ['Pulled', 'Venue', 'Location', 'PdfFile', 'Page', 'PriceEUR', 'ItemGuess', 'Slug']


def text_path(slug, url):
    return f'data/text/{slug.replace("/", "__")}__{os.path.basename(url)}.txt'


def fmt(ps):
    return ' '.join(f'{p:g}' for p in ps)


def compare(venues, pdf_results, skipped, TODAY, RAW, failed_slugs=()):
    """Returns (venue_rows, price_rows, events, first_run)."""
    prev = {(r['Slug'], r['PdfUrl']): r for r in read_csv('data/venues.csv')}
    prev_by_slug = {}
    for (slug, url), r in prev.items():
        prev_by_slug.setdefault(slug, []).append(r)
    venue_rows, price_rows, events, seen = [], [], [], set()
    for v in venues:
        seen.add(v['slug'])
        old_urls = {r['PdfUrl'] for r in prev_by_slug.get(v['slug'], []) if r['PdfUrl']}
        if not v['pdfs']:
            venue_rows.append({'Pulled': TODAY, 'Slug': v['slug'], 'Venue': v['name'], 'Location': v['location']})
            if old_urls:
                events.append(f'- **{v["name"]}** — menu PDF removed from its page (was {", ".join(os.path.basename(u) for u in old_urls)})')
            continue
        for u in v['pdfs']:
            old = prev.get((v['slug'], u))
            if u in skipped and old:
                venue_rows.append({**old, 'Pulled': TODAY})
                continue
            r = pdf_results.get(u)
            if not r:
                if old:
                    venue_rows.append(old)
                continue
            prices_sorted = sorted(p[1] for p in r['prices'])
            changed, why = False, []
            if old is None:
                if prev_by_slug.get(v['slug']):
                    changed = True
                    why.append(f'NEW PDF FILE `{os.path.basename(u)}` (was {", ".join(os.path.basename(x) for x in old_urls)})')
                elif prev:
                    events.append(f'- **{v["name"]}** — new venue on the site ({v["location"]}), menu `{os.path.basename(u)}`, {len(prices_sorted)} prices')
            else:
                if old['Sha'] != r['sha']:
                    changed = True
                    why.append('PDF bytes changed (same filename)')
                old_prices = sorted(float(x) for x in old['Prices'].split() if x)
                if old_prices != prices_sorted:
                    changed = True
                    gone = sorted((Counter(old_prices) - Counter(prices_sorted)).elements())
                    new = sorted((Counter(prices_sorted) - Counter(old_prices)).elements())
                    why.append(f'prices: {len(old_prices)} → {len(prices_sorted)}' + (f'; removed €{fmt(gone)}' if gone else '') + (f'; added €{fmt(new)}' if new else ''))
                if str(old['Pages']) != str(r['pages']):
                    why.append(f'pages {old["Pages"]} → {r["pages"]}')
            if changed:
                describe_change(v, u, r, old, prev_by_slug, why, TODAY, RAW, events, text_path, is_latin)
            venue_rows.append({'Pulled': TODAY, 'Slug': v['slug'], 'Venue': v['name'], 'Location': v['location'], 'PdfUrl': u, 'PdfFile': os.path.basename(u), 'Meta': r['meta'], 'Sha': r['sha'], 'Bytes': r['bytes'], 'Pages': r['pages'], 'PriceCount': len(prices_sorted), 'Prices': fmt(prices_sorted), 'LastChanged': TODAY if (changed or old is None) else old['LastChanged']})
            os.makedirs('data/text', exist_ok=True)
            with open(text_path(v['slug'], u), 'w', encoding='utf-8') as f:
                f.write('\n'.join(r['lines']) + '\n')
            for pg, val, name in r['prices']:
                price_rows.append({'Pulled': TODAY, 'Venue': v['name'], 'Location': v['location'], 'PdfFile': os.path.basename(u), 'Page': pg, 'PriceEUR': f'{val:g}', 'ItemGuess': name, 'Slug': v['slug']})
        for r0 in prev_by_slug.get(v['slug'], []):
            if r0['PdfUrl'] and r0['PdfUrl'] not in v['pdfs'] and os.path.exists(text_path(v['slug'], r0['PdfUrl'])):
                os.remove(text_path(v['slug'], r0['PdfUrl']))
    for slug in set(prev_by_slug) - seen:
        if slug in failed_slugs:
            venue_rows.extend(prev_by_slug[slug])
        else:
            events.append(f'- **{prev_by_slug[slug][0]["Venue"]}** — venue no longer in the Disneyland Paris sitemap')
    return venue_rows, price_rows, events, not prev
