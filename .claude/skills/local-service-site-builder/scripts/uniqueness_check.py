#!/usr/bin/env python3
"""
Check that a site's content is genuinely its own before publishing.

    python3 uniqueness_check.py <new_site_dist> --against <other_dist> [<other_dist> ...]
                                [--cross-max 0.20] [--internal-max 0.45]

Compares the main content (<main>, or the body minus header/footer/nav) of every page as overlapping
5-word sequences (shingles):

  cross-site : each page of the new site vs every page of every --against site, as containment (share of the
               smaller page found in the other). Fails above --cross-max (default 20%): copied or lightly
               reworded pages fail even when the rest of the page is new.
  internal   : each page vs the other pages of the same site, as Jaccard similarity (shared / combined text).
               Fails if any pair is more than --internal-max similar (default 50%) – catches "same page,
               different city name" doorway patterns without flagging short hub pages.

Also compares design.json files when present next to the dist folders (or one level up).
Exit code 1 on failure, so it can gate a publish step.
"""
import argparse
import itertools
import json
import os
import re
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_audit import visible_main_text  # noqa: E402
try:
    from design_seed import design_distance  # noqa: E402
except Exception:  # pragma: no cover
    design_distance = None


def shingles(text, n=5):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {' '.join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def load(site):
    pages = {}
    for dp, dns, fns in os.walk(site):
        dns[:] = [d for d in dns if d not in ('.git', 'assets', 'node_modules')]
        for f in fns:
            if not f.endswith('.html') or f == '404.html':
                continue
            raw = open(os.path.join(dp, f), encoding='utf-8', errors='ignore').read()
            if re.search(r'<meta[^>]+noindex', raw, re.I):
                continue
            soup = BeautifulSoup(raw, 'lxml')
            main = soup.find('main')
            if main:
                for t in main(['script', 'style', 'form', 'nav']):
                    t.decompose()
                text = main.get_text(' ', strip=True)
            else:
                text = visible_main_text(soup)
            url = '/' + os.path.relpath(os.path.join(dp, f), site).replace(os.sep, '/').replace('index.html', '')
            pages[url] = shingles(text)
    return pages


def jaccard(a, b):
    """Symmetric overlap: shared text / all text of both pages."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(a, b):
    """Share of the smaller page's text that also appears in the other page."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def find_design(dist):
    for p in (os.path.join(dist, 'design.json'), os.path.join(os.path.dirname(os.path.abspath(dist)), 'design.json')):
        if os.path.isfile(p):
            return json.load(open(p))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--against', nargs='*', default=[])
    ap.add_argument('--cross-max', type=float, default=0.20)
    ap.add_argument('--internal-max', type=float, default=0.50)
    ap.add_argument('--min-design-distance', type=float, default=0.5)
    a = ap.parse_args()

    new = load(a.site)
    print(f'{a.site}: {len(new)} indexable pages')
    failed = False

    worst = []
    for (u1, s1), (u2, s2) in itertools.combinations(new.items(), 2):
        c = jaccard(s1, s2)
        if c > a.internal_max:
            worst.append((c, u1, u2))
    worst.sort(reverse=True)
    if worst:
        failed = True
        print(f'FAIL internal: {len(worst)} page pairs share more than {a.internal_max:.0%} of their text')
        for c, u1, u2 in worst[:10]:
            print(f'   {c:.0%}  {u1}  <->  {u2}')
    else:
        print(f'ok   internal: no page pair above {a.internal_max:.0%}')

    d_new = find_design(a.site)
    for other in a.against:
        pages = load(other)
        hits = []
        for u1, s1 in new.items():
            best = max(((containment(s1, s2), u2) for u2, s2 in pages.items()), default=(0, ''))
            if best[0] > a.cross_max:
                hits.append((best[0], u1, best[1]))
        hits.sort(reverse=True)
        if hits:
            failed = True
            print(f'FAIL vs {other}: {len(hits)} pages share more than {a.cross_max:.0%} of their text')
            for c, u1, u2 in hits[:10]:
                print(f'   {c:.0%}  {u1}  <->  {u2}')
        else:
            top = max((max((containment(s1, s2) for s2 in pages.values()), default=0) for s1 in new.values()), default=0)
            print(f'ok   vs {other}: highest page overlap {top:.0%}')
        d_other = find_design(other)
        if d_new and d_other and design_distance:
            dist = design_distance(d_new, d_other)
            flag = 'ok  ' if dist >= a.min_design_distance else 'FAIL'
            failed |= dist < a.min_design_distance
            print(f'{flag} design distance vs {other}: {dist:.2f} (min {a.min_design_distance})')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
