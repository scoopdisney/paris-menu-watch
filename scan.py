#!/usr/bin/env python3
"""Disneyland Paris menu watch — SEPARATE from the Disneyland, WDW, Tokyo and Shanghai trackers.

Disney publishes each Disneyland Paris restaurant's menu as a PDF on media.disneylandparis.com, linked from
/en-gb/dining/<location>/<venue> (behind a Queue-it gate the cookie jar carries). 83 of 84 PDFs are real text
with euro prices, so this watcher alerts per venue on: new PDF filename, changed bytes, changed price set,
added/removed text lines, page-count change, venue added/removed. Changed PDFs are rendered to page images
and linked from the issue. PDFs total ~1GB, so unchanged files are skipped by ETag/size without downloading.

Outputs: data/venues.csv, data/prices.csv, data/text/, data/renders/, data/last-daily.txt, summary.md, POST_COMMENT
"""
import os
from datetime import datetime, timezone

from dlp_util import write_csv
from dlp_report import write_summary
from dlp_diff import compare, VEN_HEADER, PR_HEADER
from dlp_site import gather

REPO = os.environ.get('GITHUB_REPOSITORY', 'scoopdisney/paris-menu-watch')
RAW = f'https://raw.githubusercontent.com/{REPO}/main/'
NOW_DT = datetime.now(timezone.utc)
TODAY = NOW_DT.strftime('%Y-%m-%d')
NOW = NOW_DT.strftime('%Y-%m-%d %H:%M')

g = gather(NOW)
venues, failures, pdf_results, skipped = g['venues'], g['failures'], g['pdf_results'], g['skipped']

os.makedirs('data/text', exist_ok=True)
os.makedirs('data/renders', exist_ok=True)
venue_rows, price_rows, events, first_run = compare(venues, pdf_results, skipped, TODAY, RAW, g['failed_slugs'])

if skipped:
    from dlp_util import read_csv
    keep = {os.path.basename(u) for u in skipped} | {os.path.basename(r['PdfUrl']) for r in venue_rows if r.get('PdfUrl') and r['PdfUrl'] not in pdf_results}
    kept = [r for r in read_csv('data/prices.csv') if r['PdfFile'] in keep]
    price_rows = kept + price_rows
write_csv('data/venues.csv', venue_rows, VEN_HEADER)
write_csv('data/prices.csv', price_rows, PR_HEADER)

write_summary({'NOW': NOW, 'TODAY': TODAY, 'venues': venues, 'failures': failures, 'events': events, 'venue_rows': venue_rows,
               'pdf_total': len(pdf_results) + len(skipped), 'pdf_count': len(pdf_results), 'skipped': len(skipped),
               'price_count': len(price_rows), 'first_run': first_run})
