"""PDF helpers for paris-menu-watch: text lines + euro price tokens with name guesses."""
import io, re

import pdfplumber

def is_latin(w):
    return re.search(r'[A-Za-zÀ-ÿ]', w) is not None

PRICE_RE = re.compile(r'^€?(\d{1,3}(?:[,.]\d{2})?)\s?€?$')

def parse_pdf(data):
    """Returns (pages, lines, prices[(page, value, name_guess)]). Prices in EUR."""
    lines, prices = [], []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        npages = len(pdf.pages)
        for pi, pg in enumerate(pdf.pages):
            try:
                words = pg.extract_words(use_text_flow=False)
            except Exception:
                words = []
            by_line = {}
            for w in words:
                by_line.setdefault(round(w['top'] / 4), []).append(w)
            for k in sorted(by_line):
                txt = ' '.join(x['text'] for x in sorted(by_line[k], key=lambda x: x['x0']))
                if txt.strip():
                    lines.append(f'p{pi+1}: {txt}')
            for w in words:
                m = PRICE_RE.match(w['text'])
                if not m:
                    continue
                val = float(m.group(1).replace(',', '.'))
                ok = '€' in w['text']
                if not ok:
                    for v in words:
                        if v['text'].strip() == '€' and 0 <= v['x0'] - w['x1'] < 25 and abs(v['top'] - w['top']) < 4:
                            ok = True
                            break
                if not ok or not (0.5 <= val <= 999):
                    continue
                cands = [v for v in words if is_latin(v['text']) and w['top'] - 60 <= v['top'] <= w['top'] + 6
                         and v['x0'] < w['x0'] and v['x1'] > w['x0'] - 320
                         and not re.match(r'^\d+ ?(cl|ml|g|kg|l)$', v['text'], re.I) and '€' not in v['text']]
                by = {}
                for v in cands:
                    by.setdefault(round(v['top'] / 4), []).append(v)
                name_lines = []
                for k in sorted(by, reverse=True):
                    txt = ' '.join(x['text'] for x in sorted(by[k], key=lambda x: x['x0']))
                    if len(txt) < 2:
                        continue
                    name_lines.insert(0, txt)
                    if len(name_lines) >= 2:
                        break
                prices.append((pi + 1, val, re.sub(r'\s+', ' ', ' '.join(name_lines)).strip()[:120]))
    return npages, lines, prices
