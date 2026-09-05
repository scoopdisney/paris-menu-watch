"""Summary, renders and change descriptions for paris-menu-watch."""
import os, subprocess

RENDER_DPI = int(os.environ.get('RENDER_DPI', '70'))
MAX_RENDER_PAGES = int(os.environ.get('MAX_RENDER_PAGES', '8'))


def render(slug, url, data, TODAY, RAW, events):
    out, d = [], f'data/renders/{slug.replace("/", "__")}'
    os.makedirs(d, exist_ok=True)
    base = f'{d}/{TODAY}_{os.path.splitext(os.path.basename(url))[0]}'
    try:
        tmp = '/tmp/render.pdf'
        open(tmp, 'wb').write(data)
        subprocess.run(['pdftoppm', '-r', str(RENDER_DPI), '-jpeg', '-jpegopt', 'quality=60', '-l', str(MAX_RENDER_PAGES), tmp, base], check=True, timeout=180, stderr=subprocess.DEVNULL)
        out = [RAW + f'{d}/{f}' for f in sorted(os.listdir(d)) if f.startswith(os.path.basename(base))]
    except Exception as e:
        events.append(f'  - (render failed: {e})')
    return out


def describe_change(v, u, r, old, prev_by_slug, why, TODAY, RAW, events, text_path, is_latin):
    tp = text_path(v['slug'], old['PdfUrl'] if old else (prev_by_slug.get(v['slug']) or [{'PdfUrl': u}])[0]['PdfUrl'])
    old_lines = set(open(tp, encoding='utf-8').read().splitlines()) if os.path.exists(tp) else set()
    added = [l for l in r['lines'] if l not in old_lines and is_latin(l)]
    removed = [l for l in sorted(old_lines - set(r['lines'])) if is_latin(l)]
    events.append(f'- **{v["name"]}** ({v["location"]}) — ' + '; '.join(why))
    for l in added[:12]:
        events.append(f'  - + {l.split(": ", 1)[-1]}')
    if len(added) > 12:
        events.append(f'  - + …and {len(added) - 12} more new lines')
    for l in removed[:12]:
        events.append(f'  - − {l.split(": ", 1)[-1]}')
    if len(removed) > 12:
        events.append(f'  - − …and {len(removed) - 12} more removed lines')
    for i, L in enumerate(render(v['slug'], u, r['data'], TODAY, RAW, events), 1):
        events.append(f'  - [page {i}]({L})')


def write_summary(ctx):
    NOW, TODAY = ctx['NOW'], ctx['TODAY']
    venues, failures, events, venue_rows = ctx['venues'], ctx['failures'], ctx['events'], ctx['venue_rows']
    last_daily = open('data/last-daily.txt').read().strip() if os.path.exists('data/last-daily.txt') else ''
    is_daily = last_daily != TODAY
    with_pdf = sum(1 for v in venues if v['pdfs'])
    lines = [f'## Disneyland Paris menu scan {NOW} UTC', '',
             f"{len(venues)} venues on the site, {with_pdf} with a menu PDF ({ctx['pdf_total']} PDFs: {ctx['pdf_count']} downloaded, {ctx['skipped']} unchanged by ETag; {ctx['price_count']} price tokens)" + (f', {len(failures)} fetch failure(s).' if failures else ', 0 failures.'), '']
    if ctx['first_run']:
        lines += ['First run — baseline established. Nothing to diff against yet.', '', '| Venue | Location | Menu PDF | Prices |', '|---|---|---|---|']
        lines += [f'| {r["Venue"]} | {r["Location"]} | {r.get("PdfFile") or "—"} | {r.get("PriceCount") or "—"} |' for r in venue_rows]
    elif not events:
        lines.append('**Daily check complete — no menu changes.**' if is_daily else '**No changes.**')
    else:
        n = len([e for e in events if e.startswith('- ')])
        lines.append(f'### {n} menu change{"s" if n != 1 else ""}')
        lines.extend(events)
    if failures:
        lines += ['', '### Fetch failures'] + ['- ' + f for f in failures]
    lines += ['', '---', '_Alerts are per menu PDF: new file, changed bytes, changed price set, added/removed text. Prices in EUR, tax included. Item-to-price pairing in data/prices.csv is a best-effort guess from PDF layout; the rendered page images are the source of truth._']
    has_news = ctx['first_run'] or bool(events) or bool(failures)
    if has_news or is_daily:
        open('POST_COMMENT', 'w').write('1')
    if is_daily:
        open('data/last-daily.txt', 'w').write(TODAY + '\n')
    open('summary.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('NEWS: comment will post' if has_news else ('DAILY: comment will post' if is_daily else 'QUIET: no comment this run'))
