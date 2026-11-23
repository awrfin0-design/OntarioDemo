#!/usr/bin/env python3
"""
Static-site SEO audit.

Usage:
    python3 seo_audit.py <site_dir> [--out report.json] [--md report.md] [--site-url https://example.com]

Walks every *.html page under <site_dir> (directory-style URLs: foo/index.html -> /foo/),
and reports per-page and site-wide SEO problems:

  titles / meta descriptions (missing, length, duplicates), H1s, canonical, robots meta,
  lang, viewport, Open Graph, image alt/size/lazy-loading, JSON-LD validity and types,
  broken internal links, thin content, HTML weight, robots.txt / sitemap.xml,
  and near-duplicate content clusters (MinHash over 5-word shingles).

Needs: beautifulsoup4 + lxml (pip install beautifulsoup4 lxml).
"""
import argparse
import collections
import hashlib
import json
import os
import posixpath
import re
import sys
from concurrent.futures import ProcessPoolExecutor

from bs4 import BeautifulSoup

SKIP_DIRS = {'.git', 'node_modules', 'dist', '.claude'}
NUM_HASH = 64
BANDS, ROWS = 16, 4          # LSH: 16 bands x 4 rows -> catches Jaccard >~0.6
DUP_THRESHOLD = 0.80         # report pairs at or above this estimated similarity
MASKS = [int(hashlib.md5(str(i).encode()).hexdigest()[:16], 16) for i in range(NUM_HASH)]


def url_of(rel):
    rel = rel.replace(os.sep, '/')
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel


def visible_main_text(soup):
    for t in soup(['script', 'style', 'noscript', 'svg', 'template', 'iframe']):
        t.decompose()
    for sel in ['header', 'footer', 'nav', '.modal', '.main-header', '.main-footer', '.sticky-header',
                '.mobile-menu', '.search-popup', '[aria-hidden=true]']:
        for t in soup.select(sel):
            t.decompose()
    body = soup.body or soup
    return re.sub(r'\s+', ' ', body.get_text(' ', strip=True))


def minhash(text):
    words = re.findall(r'[a-z0-9]+', text.lower())
    shingles = {' '.join(words[i:i + 5]) for i in range(max(1, len(words) - 4))}
    hs = [int(hashlib.md5(s.encode()).hexdigest()[:16], 16) for s in shingles] or [0]
    return [min(h ^ m for h in hs) for m in MASKS]


def audit_page(args):
    root, rel = args
    path = os.path.join(root, rel)
    raw = open(path, encoding='utf-8', errors='ignore').read()
    soup = BeautifulSoup(raw, 'lxml')
    d = {'url': url_of(rel), 'file': rel, 'bytes': len(raw.encode('utf-8', 'ignore'))}
    html = soup.find('html')
    d['lang'] = html.get('lang') if html else None
    d['title'] = soup.title.get_text(strip=True) if soup.title else None

    def meta(**kw):
        m = soup.find('meta', attrs=kw)
        return m.get('content') if m else None

    d['description'] = meta(name='description')
    d['robots'] = meta(name='robots')
    d['viewport'] = bool(meta(name='viewport'))
    canon = soup.find('link', rel=lambda v: v and 'canonical' in v)
    d['canonical'] = canon.get('href') if canon else None
    d['og'] = {k: meta(property='og:' + k) for k in ('title', 'description', 'image', 'url')}
    d['h1'] = [re.sub(r'\s+', ' ', h.get_text(' ', strip=True)) for h in soup.find_all('h1')]
    d['h2_count'] = len(soup.find_all('h2'))

    imgs = soup.find_all('img')
    d['img_total'] = len(imgs)
    d['img_no_alt'] = sum(1 for i in imgs if i.get('alt') is None)
    d['img_empty_alt'] = sum(1 for i in imgs if i.get('alt') == '')
    d['img_no_size'] = sum(1 for i in imgs if not (i.get('width') and i.get('height')))
    d['img_not_lazy'] = sum(1 for i in imgs if i.get('loading') != 'lazy')

    ld_types, ld_errors = [], 0
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(s.string or '')
        except Exception:
            ld_errors += 1
            continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                t = x.get('@type')
                if t:
                    ld_types.extend(t if isinstance(t, list) else [t])
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
    d['jsonld_types'] = sorted(set(ld_types))
    d['jsonld_errors'] = ld_errors

    base = posixpath.dirname(rel.replace(os.sep, '/'))
    links = []
    for a in soup.find_all('a', href=True):
        h = a['href'].split('#')[0].split('?')[0].strip()
        if not h or re.match(r'^(https?:|//|tel:|mailto:|javascript:|data:)', h) or '{' in h or 'item.' in h:
            continue
        links.append(posixpath.normpath(posixpath.join(base, h)).lstrip('./') if not h.startswith('/') else h.lstrip('/'))
    d['internal_links'] = sorted(set(links))

    text = visible_main_text(soup)
    d['words'] = len(text.split())
    d['minhash'] = minhash(text)
    return d


def link_ok(root, target):
    target = re.sub(r'^(\.\./)+', '', target)
    p = os.path.join(root, target)
    return os.path.isfile(p) or os.path.isfile(os.path.join(p, 'index.html'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site_dir')
    ap.add_argument('--out', default=None)
    ap.add_argument('--md', default=None)
    ap.add_argument('--site-url', default=None, help='expected canonical origin, e.g. https://example.com')
    a = ap.parse_args()
    root = os.path.abspath(a.site_dir)

    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [x for x in dns if x not in SKIP_DIRS]
        for f in fns:
            if f.endswith('.html'):
                files.append(os.path.relpath(os.path.join(dp, f), root))
    files.sort()
    with ProcessPoolExecutor() as ex:
        pages = list(ex.map(audit_page, [(root, f) for f in files], chunksize=16))

    n = len(pages)
    issues = collections.OrderedDict()

    def add(key, label, severity, urls):
        urls = sorted(set(urls))
        if urls:
            issues[key] = {'label': label, 'severity': severity, 'count': len(urls), 'examples': urls[:8]}

    add('no_title', 'Missing <title>', 'high', [p['url'] for p in pages if not p['title']])
    add('title_long', 'Title longer than 60 characters (truncated in results)', 'low',
        [p['url'] for p in pages if p['title'] and len(p['title']) > 60])
    add('title_short', 'Title shorter than 25 characters', 'low',
        [p['url'] for p in pages if p['title'] and len(p['title']) < 25])
    add('no_desc', 'Missing meta description', 'medium', [p['url'] for p in pages if not p['description']])
    add('desc_len', 'Meta description outside 70-160 characters', 'low',
        [p['url'] for p in pages if p['description'] and not 70 <= len(p['description']) <= 160
         and not (p['robots'] and 'noindex' in p['robots'].lower())])
    add('h1_none', 'No <h1>', 'medium', [p['url'] for p in pages if not p['h1']])
    add('h1_multi', 'More than one <h1>', 'low', [p['url'] for p in pages if len(p['h1']) > 1])
    add('no_canonical', 'Missing canonical link', 'high', [p['url'] for p in pages if not p['canonical']])
    add('canonical_relative', 'Canonical is not an absolute URL', 'medium',
        [p['url'] for p in pages if p['canonical'] and not p['canonical'].startswith('http')])
    if a.site_url:
        add('canonical_foreign', 'Canonical points to a different domain than --site-url', 'high',
            [p['url'] for p in pages if p['canonical'] and p['canonical'].startswith('http')
             and not p['canonical'].startswith(a.site_url.rstrip('/'))])
    add('noindex', 'Page has robots noindex', 'info',
        [p['url'] for p in pages if p['robots'] and 'noindex' in p['robots'].lower()])
    add('no_lang', 'Missing <html lang>', 'low', [p['url'] for p in pages if not p['lang']])
    add('no_viewport', 'Missing viewport meta', 'medium', [p['url'] for p in pages if not p['viewport']])
    add('og_incomplete', 'Open Graph tags incomplete (title/description/image/url)', 'low',
        [p['url'] for p in pages if not all(p['og'].values())])
    add('og_url_relative', 'og:url / og:image not absolute', 'low',
        [p['url'] for p in pages if any(v and not v.startswith('http') for k, v in p['og'].items() if k in ('url', 'image'))])
    add('img_no_alt', 'Images with no alt attribute', 'medium', [p['url'] for p in pages if p['img_no_alt']])
    add('img_no_size', 'Images without width/height (layout shift)', 'low', [p['url'] for p in pages if p['img_no_size']])
    add('jsonld_errors', 'Invalid JSON-LD', 'high', [p['url'] for p in pages if p['jsonld_errors']])
    add('no_jsonld', 'No structured data', 'low', [p['url'] for p in pages if not p['jsonld_types']])
    add('thin', 'Thin content (< 300 words of main text, indexable pages)', 'medium',
        [p['url'] for p in pages if p['words'] < 300 and not (p['robots'] and 'noindex' in p['robots'].lower())])
    add('heavy_html', 'HTML document > 100 KB', 'low', [p['url'] for p in pages if p['bytes'] > 100_000])

    broken = collections.Counter()
    broken_pages = []
    for p in pages:
        bad = [t for t in p['internal_links'] if not link_ok(root, t)]
        if bad:
            broken_pages.append(p['url'])
            broken.update(bad)
    add('broken_links', 'Pages linking to missing internal pages', 'high', broken_pages)

    for key, label in (('title', 'Duplicate titles'), ('description', 'Duplicate meta descriptions')):
        groups = collections.defaultdict(list)
        for p in pages:
            if p[key]:
                groups[p[key].strip().lower()].append(p['url'])
        dups = [u for g in groups.values() if len(g) > 1 for u in g]
        add('dup_' + key, label, 'medium', dups)
        issues.get('dup_' + key, {})['groups'] = sum(1 for g in groups.values() if len(g) > 1)
    h1g = collections.defaultdict(list)
    for p in pages:
        if p['h1']:
            h1g[p['h1'][0].lower()].append(p['url'])
    add('dup_h1', 'Duplicate H1s', 'low', [u for g in h1g.values() if len(g) > 1 for u in g])

    # near-duplicate content via MinHash LSH
    buckets = collections.defaultdict(list)
    for i, p in enumerate(pages):
        mh = p['minhash']
        for b in range(BANDS):
            buckets[(b, tuple(mh[b * ROWS:(b + 1) * ROWS]))].append(i)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pairs = 0
    seen = set()
    for members in buckets.values():
        if len(members) < 2 or len(members) > 2000:
            continue
        a0 = members[0]
        for j in members[1:]:
            key = (min(a0, j), max(a0, j))
            if key in seen:
                continue
            seen.add(key)
            sim = sum(x == y for x, y in zip(pages[a0]['minhash'], pages[j]['minhash'])) / NUM_HASH
            if sim >= DUP_THRESHOLD:
                pairs += 1
                parent[find(a0)] = find(j)
    clusters = collections.defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(pages[i]['url'])
    dup_clusters = sorted((c for c in clusters.values() if len(c) > 1), key=len, reverse=True)
    dup_urls = [u for c in dup_clusters for u in c]
    add('near_duplicate', 'Near-duplicate main content (>= 80% similar to another page)', 'high', dup_urls)
    if 'near_duplicate' in issues:
        issues['near_duplicate']['clusters'] = len(dup_clusters)
        issues['near_duplicate']['largest_clusters'] = [{'size': len(c), 'examples': c[:6]} for c in dup_clusters[:8]]

    site = {
        'robots_txt': os.path.isfile(os.path.join(root, 'robots.txt')),
        'sitemap_xml': os.path.isfile(os.path.join(root, 'sitemap.xml')),
        'custom_404': os.path.isfile(os.path.join(root, '404.html')),
    }
    stats = {
        'pages': n,
        'avg_words': round(sum(p['words'] for p in pages) / max(n, 1)),
        'median_html_kb': sorted(p['bytes'] for p in pages)[n // 2] // 1024 if n else 0,
        'jsonld_types': collections.Counter(t for p in pages for t in p['jsonld_types']).most_common(12),
        'top_broken_targets': broken.most_common(10),
    }
    report = {'site': site, 'stats': stats, 'issues': issues}
    if a.out:
        json.dump({**report, 'pages': [{k: v for k, v in p.items() if k != 'minhash'} for p in pages]},
                  open(a.out, 'w'), indent=1)
    lines = [f"# SEO audit: {n} pages", '',
             f"robots.txt: {site['robots_txt']} | sitemap.xml: {site['sitemap_xml']} | 404.html: {site['custom_404']}",
             f"Average main-content words: {stats['avg_words']} | Median HTML size: {stats['median_html_kb']} KB", '',
             '| Severity | Issue | Pages | Examples |', '|---|---|---|---|']
    order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
    for k, v in sorted(issues.items(), key=lambda kv: (order[kv[1]['severity']], -kv[1]['count'])):
        lines.append(f"| {v['severity']} | {v['label']} | {v['count']} | {', '.join(v['examples'][:3])} |")
    text = '\n'.join(lines)
    if a.md:
        open(a.md, 'w').write(text + '\n')
    print(text)
    if 'near_duplicate' in issues:
        print('\nLargest near-duplicate clusters:')
        for c in issues['near_duplicate']['largest_clusters']:
            print(f"  {c['size']:5d} pages, e.g. {', '.join(c['examples'][:4])}")
    if stats['top_broken_targets']:
        print('\nMost-linked missing targets:', stats['top_broken_targets'][:5])


if __name__ == '__main__':
    main()
