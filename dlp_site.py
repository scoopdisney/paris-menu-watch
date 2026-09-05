"""Site + PDF gathering for paris-menu-watch: sitemap discovery, venue pages, conditional PDF download/parse."""
import hashlib, os, re, sys
from concurrent.futures import ThreadPoolExecutor

from menu_pdf import parse_pdf
from dlp_util import get, head, strip_html, read_csv

SITEMAP = 'https://api.disneylandparis.com/sitemaps/marketing/sitemap.xml'
HOST = 'https://www.disneylandparis.com'
LOC_NAMES = {'disneyland-park': 'Disneyland Park', 'disney-adventure-world': 'Disney Adventure World', 'disney-village': 'Disney Village',
             'disneyland-hotel': 'Disneyland Hotel', 'disneys-hotel-new-york': "Disney's Hotel New York", 'disneys-newport-bay-club': "Disney's Newport Bay Club",
             'disneys-sequoia-lodge': "Disney's Sequoia Lodge", 'disneys-hotel-cheyenne': "Disney's Hotel Cheyenne", 'disneys-hotel-santa-fe': "Disney's Hotel Santa Fe",
             'disneys-davy-crockett-ranch': "Disney's Davy Crockett Ranch", 'golf-disneyland': 'Golf Disneyland'}


def gather(NOW):
    """Returns dict(venues, failures, pdf_results, skipped). Calls abort() (exit 0) on structural failures."""
    def abort(reason):
        os.makedirs('data', exist_ok=True)
        with open('summary.md', 'w', encoding='utf-8') as f:
            f.write(f'## Paris menu scan {NOW} UTC — ABORTED\n\n{reason}\n\nSnapshot left untouched.\n')
        open('POST_COMMENT', 'w').write('1')
        print('ABORTED:', reason)
        sys.exit(0)

    try:
        parts = re.findall(r'<loc>([^<]+)</loc>', get(SITEMAP))
        urls = set()
        for p in parts:
            urls.update(re.findall(r'<loc>(https://www\.disneylandparis\.com/en-gb/dining/[a-z0-9-]+/[a-z0-9-]+)</loc>', get(p)))
    except Exception as e:
        abort(f'Could not read the Disneyland Paris sitemaps: {e}')
    urls = sorted(u for u in urls if not u.endswith('/map'))
    if len(urls) < 60:
        abort(f'Sitemaps listed only {len(urls)} dining pages (expected ~100). Site structure may have changed.')

    def venue_info(url):
        h = get(url)
        title = re.search(r'<title>([^<]*)</title>', h)
        name = re.sub(r'\s*[-|].*$', '', strip_html(title.group(1))) if title else url.rsplit('/', 1)[-1]
        loc_slug, slug = url.split('/en-gb/dining/')[1].split('/')
        pdfs = sorted(set(re.findall(r'https://media\.disneylandparis\.com/[^"\'\\\s<>]+?\.pdf', h)))
        return {'slug': f'{loc_slug}/{slug}', 'name': name, 'location': LOC_NAMES.get(loc_slug, loc_slug), 'pdfs': pdfs, 'url': url}

    failures, venues, failed_slugs = [], [], set()
    def _safe(u):
        try:
            return venue_info(u)
        except Exception as e:
            return {'slug': u, 'error': str(e)}
    with ThreadPoolExecutor(4) as ex:
        for v in ex.map(_safe, urls):
            if 'error' in v:
                failures.append(f"{v['slug']}: {v['error']}")
                failed_slugs.add(v['slug'].split('/en-gb/dining/')[-1])
            else:
                venues.append(v)
    if len(failures) > 10:
        abort(f'{len(failures)} venue pages failed (Queue-it gate?):\n' + '\n'.join('- ' + f for f in failures))

    prev_meta = {r['PdfUrl']: r.get('Meta', '') for r in read_csv('data/venues.csv')}
    pdf_jobs = sorted({u for v in venues for u in v['pdfs']})
    pdf_results, skipped = {}, {}

    def fetch(url):
        meta = head(url)
        if meta and meta == prev_meta.get(url):
            return url, {'skip': True, 'meta': meta}
        data = get(url, timeout=300, binary=True)
        if not data.startswith(b'%PDF'):
            raise RuntimeError('not a PDF')
        pages, lines, prices = parse_pdf(data)
        return url, {'url': url, 'sha': hashlib.sha256(data).hexdigest()[:16], 'bytes': len(data), 'pages': pages, 'lines': lines, 'prices': prices, 'data': data, 'meta': meta or f'|{len(data)}'}

    def _safe_pdf(u):
        try:
            return fetch(u)
        except Exception as e:
            return u, {'error': str(e)}
    with ThreadPoolExecutor(4) as ex:
        for u, r in ex.map(_safe_pdf, pdf_jobs):
            if 'error' in r:
                failures.append(f'{os.path.basename(u)}: {r["error"]}')
            elif r.get('skip'):
                skipped[u] = r['meta']
            else:
                pdf_results[u] = r
    if len(pdf_results) + len(skipped) < max(10, len(pdf_jobs) - 6):
        abort(f'Only {len(pdf_results) + len(skipped)} of {len(pdf_jobs)} menu PDFs reachable.\n' + '\n'.join('- ' + f for f in failures))
    return {'venues': venues, 'failures': failures, 'pdf_results': pdf_results, 'skipped': skipped, 'failed_slugs': failed_slugs}
