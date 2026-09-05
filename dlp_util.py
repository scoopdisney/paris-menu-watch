"""HTTP (with the Queue-it cookie jar), HEAD metadata and CSV helpers for paris-menu-watch."""
import csv, html, http.cookiejar, os, re, time
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPCookieProcessor

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'
_JAR = http.cookiejar.CookieJar()
_OPENER = build_opener(HTTPCookieProcessor(_JAR))


def get(url, timeout=90, binary=False):
    last = None
    for attempt in range(1, 4):
        try:
            req = Request(quote(url, safe=':/?&=%'), headers={'User-Agent': UA, 'Accept-Language': 'en-GB,en;q=0.9'})
            with _OPENER.open(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else data.decode('utf-8', 'ignore')
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * attempt)
    raise last


def head(url, timeout=30):
    """Returns 'etag|content-length' so unchanged PDFs can be skipped without downloading 10-40MB each."""
    try:
        req = Request(quote(url, safe=':/?&=%'), method='HEAD', headers={'User-Agent': UA})
        with _OPENER.open(req, timeout=timeout) as r:
            et = re.sub(r'^W/|"', '', r.headers.get('ETag') or '')
            return et or f"len|{r.headers.get('Content-Length') or ''}"
    except Exception:
        return ''


def strip_html(h):
    t = re.sub(r'<script.*?</script>', ' ', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    return html.unescape(re.sub(r'\s+', ' ', t)).strip()


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, header):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in header})
