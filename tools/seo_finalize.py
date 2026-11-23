#!/usr/bin/env python3
"""
Domain-dependent SEO step. Run once you know where the site will live:

    python3 tools/seo_finalize.py --site-url https://www.yourdomain.ca

  - Makes canonical, og:url, og:image, twitter:image and JSON-LD url/image values absolute.
  - Writes sitemap.xml (indexable pages only: skips noindex pages and pages whose canonical
    points elsewhere) and robots.txt pointing to it.

Re-runnable: it rewrites root-relative and previously finalized URLs to the new --site-url.
"""
import argparse
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'.git', 'dist', '.claude', 'tools', 'node_modules'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site-url', required=True)
    ap.add_argument('--exclude', nargs='*', default=[], help='URL prefixes to leave out of the sitemap, e.g. /acton/')
    a = ap.parse_args()
    origin = a.site_url.rstrip('/')
    prev = re.compile(r'https?://[^/"\s>]+(?=/)')  # any previously finalized origin

    entries = []
    today = datetime.date.today().isoformat()
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP]
        if 'index.html' not in fns:
            continue
        rel = os.path.relpath(os.path.join(dp, 'index.html'), ROOT).replace(os.sep, '/')
        url = '/' if rel == 'index.html' else '/' + rel[:-len('index.html')]
        depth = rel.count('/')
        p = os.path.join(ROOT, rel)
        h = open(p, encoding='utf-8').read()

        def absolute(value):
            value = value.strip('"\'')
            if value.startswith('http'):
                return prev.sub(origin, value, count=1)
            v = re.sub(r'^(\.\./)+', '', value)
            return origin + (v if v.startswith('/') else '/' + v)

        h = re.sub(r'<link href=([^\s>]+) rel=canonical>', lambda m: f'<link href={absolute(m.group(1))} rel=canonical>', h)
        canon = re.search(r'<link href=([^\s>]+) rel=canonical>', h)
        canon_url = canon.group(1) if canon else origin + url
        # og:url always = canonical; images absolute
        h = re.sub(r'<meta content=[^\s>]* property=og:url>', f'<meta content={canon_url} property=og:url>', h)
        for prop in (r'property=og:image', r'property=og:image:secure_url', r'name=twitter:image'):
            h = re.sub(r'<meta content=([^\s>]+) ' + prop + '>',
                       lambda m, prop=prop: f'<meta content={absolute(m.group(1))} {prop}>', h)

        def fix_ld(m):
            try:
                data = json.loads(m.group(2))
            except Exception:
                return m.group(0)

            def walk(x):
                if isinstance(x, dict):
                    for k, v in list(x.items()):
                        if k in ('url', 'image', 'logo', '@id') and isinstance(v, str) and not v.startswith(('tel:', 'mailto:')):
                            x[k] = absolute(v) if not v.startswith('http') else prev.sub(origin, v, count=1)
                        else:
                            walk(v)
                elif isinstance(x, list):
                    for v in x:
                        walk(v)
            walk(data)
            return m.group(1) + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '</script>'
        h = re.sub(r'(<script type=application/ld\+json>)(.*?)</script>', fix_ld, h, flags=re.S)
        open(p, 'w', encoding='utf-8').write(h)

        noindex = re.search(r'<meta[^>]*noindex[^>]*>', h)
        if noindex or canon_url != origin + url or any(url.startswith(x) for x in a.exclude):
            continue
        entries.append(origin + url)

    entries.sort(key=lambda u: (u.count('/'), u))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f'<url><loc>{u}</loc><lastmod>{today}</lastmod></url>' for u in entries]
    xml.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('\n'.join(xml) + '\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(
        f'User-agent: *\nAllow: /\nDisallow: /thank-you/\n\nSitemap: {origin}/sitemap.xml\n')
    print(f'Finalized for {origin}: {len(entries)} URLs in sitemap.xml, robots.txt written.')


if __name__ == '__main__':
    main()
