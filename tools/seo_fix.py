#!/usr/bin/env python3
"""
Technical SEO fixes for this site that don't depend on the final domain.
Safe to re-run: every change checks whether it was already applied.

    python3 tools/seo_fix.py

What it does (per page, as in-place text edits so the original markup is otherwise untouched):
  1. Adds a root-relative canonical link (absolute once tools/seo_finalize.py is run with the domain).
     Brand pages that are exact copies (e.g. /napoleon--gas-fireplace-repair/ = /napoleon--brand/)
     point their canonical at the /<brand>--brand/ page.
  2. Keeps a single <h1>: the second one ("Gas Running But Something's Off? ...") becomes an <h2>
     with identical styling.
  3. Adds width/height to images (prevents layout shift) and loading="lazy" + decoding="async"
     to images below the first section.
  4. Repoints links to city/service pages that don't exist (e.g. /acton/furnace-repair/, which is
     a 404 on the original site too) to the matching service page (/furnace-repair/).
  5. noindex on /thank-you/ and on site-index.html (still followed).
  6. Replaces the 519 KB favicon with small PNG icons.
  7. Hero background video only loads on screens >= 992px wide (phones get the poster image),
     and the poster is preloaded.
"""
import os
import re
import posixpath
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'.git', 'dist', '.claude', 'tools', 'node_modules'}
FAVICON = '_resources/images/logo/gasservicestoronto-ca_3.png'
ICONS = {'favicon-32.png': 32, 'favicon-192.png': 192, 'apple-touch-icon.png': 180}
_dims = {}


def img_size(path):
    if path not in _dims:
        try:
            with Image.open(path) as im:
                _dims[path] = im.size
        except Exception:
            _dims[path] = None
    return _dims[path]


def page_url(rel):
    return '/' if rel == 'index.html' else '/' + rel[:-len('index.html')]


def make_icons():
    src = os.path.join(ROOT, FAVICON)
    out = os.path.join(ROOT, 'assets/icons')
    os.makedirs(out, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert('RGBA')
        side = max(im.size)
        sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        for name, px in ICONS.items():
            sq.resize((px, px), Image.LANCZOS).save(os.path.join(out, name), optimize=True)


def fix_page(rel, h, brand_dupes):
    depth = rel.count('/')
    pre = '../' * depth
    base = posixpath.dirname(rel)
    url = page_url(rel)
    changed = []

    # 1. canonical
    if 'rel=canonical' not in h and 'rel="canonical"' not in h:
        canon = brand_dupes.get(url, url)
        if '<meta charset=utf-8>' in h:
            h = h.replace('<meta charset=utf-8>', f'<meta charset=utf-8><link href={canon} rel=canonical>', 1)
            changed.append('canonical')

    # 5. noindex
    if url in ('/thank-you/',) or rel == 'site-index.html':
        if 'noindex' not in h:
            if re.search(r'<meta content=INDEX,FOLLOW name=robots>', h):
                h = h.replace('<meta content=INDEX,FOLLOW name=robots>', '<meta content="noindex,follow" name=robots>')
            else:
                h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="robots" content="noindex,follow">', 1)
            changed.append('noindex')

    # 2. single h1
    h1s = list(re.finditer(r'<h1\b', h))
    if len(h1s) > 1:
        def demote(m):
            return '<h2 class=bd-title>' + m.group(1) + '</h2>'
        h, n = re.subn(r'(?<=<div class=blog-details-content>)<h1>(.*?)</h1>', demote, h, count=1)
        if n:
            changed.append('h1')
    if 'class=bd-title' in h and '.bd-title{' not in h:
        h = re.sub(r'(?=<body\b)', '<style>.blog-details-content h2.bd-title{font-size:40px!important;'
                   'line-height:48px!important;font-weight:400!important;margin:0!important;color:#222!important;'
                   'opacity:1!important;font-family:Barlow,sans-serif;letter-spacing:normal;text-transform:none}'
                   '</style>', h, count=1)
        changed.append('h1-style')

    # 3. images
    first_section_end = h.find('</section>')
    out, last, n_img = [], 0, 0
    for m in re.finditer(r'<img\b[^>]*>', h):
        tag = m.group(0)
        new = tag
        src_m = re.search(r'\bsrc=("([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag)
        src = (src_m.group(2) or src_m.group(3) or src_m.group(4)) if src_m else ''
        if src and not src.startswith(('data:', 'http', '//')) and not re.search(r'\bwidth=', tag):
            p = os.path.join(ROOT, re.sub(r'^(\.\./)+', '', posixpath.normpath(posixpath.join(base, src.split('?')[0]))).lstrip('/'))
            size = img_size(p) if os.path.isfile(p) else None
            if size:
                new = new.replace('<img', f'<img width={size[0]} height={size[1]}', 1)
        if m.start() > first_section_end > 0:
            if 'loading=' not in new:
                new = new.replace('<img', '<img loading=lazy', 1)
            if 'decoding=' not in new:
                new = new.replace('<img', '<img decoding=async', 1)
        if new != tag:
            n_img += 1
        out.append(h[last:m.start()])
        out.append(new)
        last = m.end()
    out.append(h[last:])
    h = ''.join(out)
    if n_img:
        changed.append(f'img:{n_img}')

    # 4. broken city/service links -> top-level service page
    def relink(m):
        href = m.group(1)
        if href.startswith(('http', '//', 'tel:', 'mailto:', '#', 'javascript')) or '{' in href:
            return m.group(0)
        target = posixpath.normpath(posixpath.join(base, href.split('#')[0])).lstrip('/')
        target = re.sub(r'^(\.\./)+', '', target)
        if not target or target == '.' or re.search(r'\.\w{2,4}$', target):
            return m.group(0)
        if os.path.isfile(os.path.join(ROOT, target, 'index.html')) or os.path.isfile(os.path.join(ROOT, target)):
            return m.group(0)
        slug = target.rstrip('/').split('/')[-1]
        if os.path.isfile(os.path.join(ROOT, slug, 'index.html')):
            return f'href={pre}{slug}/'
        return m.group(0)
    h2 = re.sub(r'href=([^\s>"\']+)', relink, h)
    if h2 != h:
        changed.append('links')
        h = h2

    # 6. favicon
    if FAVICON in h:
        for rel_attr in ('rel=icon type=image/x-icon', 'rel="shortcut icon" type=image/x-icon'):
            h = h.replace(f'<link href={pre}{FAVICON} {rel_attr}>', '')
        h = h.replace(f'<link href={pre}{FAVICON} rel=apple-touch-icon>',
                      f'<link href={pre}assets/icons/favicon-32.png rel=icon sizes=32x32 type=image/png>'
                      f'<link href={pre}assets/icons/favicon-192.png rel=icon sizes=192x192 type=image/png>'
                      f'<link href={pre}assets/icons/apple-touch-icon.png rel=apple-touch-icon>')
        h = h.replace(f'<meta content={pre}{FAVICON} name=msapplication-TileImage>',
                      f'<meta content={pre}assets/icons/favicon-192.png name=msapplication-TileImage>')
        changed.append('favicon')

    # 7. hero video: desktop only
    if '<video' in h and 'data-desktop-video' not in h and 'data-hero-video' not in h:
        vm = re.search(r'<video\b[^>]*>((?:<source[^>]*>)+)</video>', h)
        if vm:
            video = vm.group(0)
            new = re.sub(r'<source src=', '<source data-src=', video).replace('<video', '<video data-desktop-video', 1)
            new = new.replace(' autoplay', '').replace(' preload=metadata', ' preload=none')
            loader = ('<script>(function(){var v=document.querySelector("video[data-desktop-video]");'
                      'if(!v)return;var c=navigator.connection;'
                      'if(!window.matchMedia("(min-width: 992px)").matches||(c&&c.saveData))return;'
                      'v.querySelectorAll("source[data-src]").forEach(function(s){s.src=s.getAttribute("data-src")});'
                      'v.autoplay=true;v.load();var p=v.play();if(p&&p.catch)p.catch(function(){})})();</script>')
            h = h.replace(video, new + loader, 1)
            poster = re.search(r'poster=([^\s>]+)', new)
            if poster and 'rel=preload as=image' not in h:
                h = h.replace('</title>', f'</title><link as=image href={poster.group(1)} rel=preload>', 1)
            changed.append('video')
    return h, changed


def main():
    make_icons()
    pages = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP]
        for f in fns:
            if f == 'index.html' or (dp == ROOT and f == 'site-index.html'):
                pages.append(os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, '/'))
    # exact-duplicate brand pages: /<brand>--<service>-repair/ duplicates /<brand>--brand/
    brand_dupes = {}
    for rel in pages:
        m = re.match(r'^([a-z0-9-]+)--(?!brand/)[a-z0-9-]+/index\.html$', rel)
        if m and os.path.isfile(os.path.join(ROOT, m.group(1) + '--brand/index.html')):
            brand_dupes[page_url(rel)] = f'/{m.group(1)}--brand/'
    stats = {}
    for rel in pages:
        p = os.path.join(ROOT, rel)
        h = open(p, encoding='utf-8').read()
        h2, changed = fix_page(rel, h, brand_dupes)
        if h2 != h:
            open(p, 'w', encoding='utf-8').write(h2)
        for c in changed:
            stats[c.split(':')[0]] = stats.get(c.split(':')[0], 0) + 1
    print(f'{len(pages)} pages processed; brand duplicates canonicalised: {len(brand_dupes)}')
    print('pages changed per fix:', stats)


if __name__ == '__main__':
    main()
