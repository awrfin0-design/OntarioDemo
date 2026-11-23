#!/usr/bin/env python3
"""
Build a complete static local-service website from a site folder.

    python3 build_site.py <site_dir> [--out <dir>] [--allow-thin]

<site_dir> contains:
    site.json             business facts, services, areas, pricing, reviews, domain (see references/site-json.md)
    design.json           from design_seed.py
    content/home.json     homepage copy
    content/about.json, content/contact.json
    content/services/<slug>.json   one per service in site.json
    content/areas/<slug>.json      optional: an area page is built ONLY when this file exists
    assets/               optional real photos / logo (copied as-is)

Output (default <site_dir>/dist): plain HTML/CSS/JS, no build tools needed to host it. Includes canonical
URLs, Open Graph, JSON-LD (business, WebSite, BreadcrumbList, Service, FAQPage), sitemap.xml, robots.txt,
a 404 page, a working quote form and (if site.json has "pricing") a regional pricing calculator.

The build refuses to finish (exit 1) when a page is thin, has placeholder text, or misses SEO fields,
so nothing half-written gets published. --allow-thin turns those errors into warnings for drafts.
"""
import argparse
import datetime
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_WORDS = {'service': 300, 'area': 250, 'home': 350, 'about': 150}  # floors, override with site.json "min_words"
PLACEHOLDER = re.compile(r'lorem ipsum|\bTODO\b|\bTBD\b|\[(city|area|business|name|phone)\]|\{\{|XXX|example\.com|555-01',
                         re.I)
SCHEMA_TYPES = {  # schema.org LocalBusiness subtypes; anything else falls back to HomeAndConstructionBusiness
    'hvac': 'HVACBusiness', 'plumbing': 'Plumber', 'electrical': 'Electrician', 'roofing': 'RoofingContractor',
    'painting': 'HousePainter', 'locksmith': 'Locksmith', 'moving': 'MovingCompany',
    'general-contractor': 'GeneralContractor', 'default': 'HomeAndConstructionBusiness',
}
ICONS = {  # 24x24 stroke icons, used with currentColor
    'check': '<path d="M20 6 9 17l-5-5"/>',
    'phone': '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    'pin': '<path d="M12 22s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'shield': '<path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    'star': '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
    'tool': '<path d="M14.7 6.3a4 4 0 0 0 5 5L22 13.6 13.6 22l-2.3-2.3a4 4 0 0 0-5-5L2 10.4 10.4 2z"/>',
    'arrow': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'menu': '<path d="M4 6h16M4 12h16M4 18h16"/>',
    'chev': '<path d="m6 9 6 6 6-6"/>',
    'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
}


def esc(s):
    return html.escape(str(s or ''), quote=True)


def icon(name, size=20):
    return (f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def words(*htmls):
    text = ' '.join(re.sub(r'<[^>]+>', ' ', h or '') for h in htmls)
    return len(re.findall(r"[A-Za-z0-9']+", text))


class Site:
    def __init__(self, src, out, allow_thin):
        self.src, self.out, self.allow_thin = src, out, allow_thin
        self.cfg = json.load(open(os.path.join(src, 'site.json')))
        self.d = json.load(open(os.path.join(src, 'design.json')))
        self.p = self.d['class_prefix']
        MIN_WORDS.update(self.cfg.get('min_words', {}))
        self.origin = self.cfg['domain'].rstrip('/')
        self.biz = self.cfg['business']
        self.errors, self.warnings, self.pages = [], [], []
        self.services = self.cfg['services']
        self.areas = self.cfg.get('areas', [])
        self.area_pages = [a for a in self.areas if os.path.isfile(os.path.join(src, 'content/areas', a['slug'] + '.json'))]
        if self.cfg.get('example'):
            self.warn('site.json', 'EXAMPLE SITE: fictional business, for testing the skill only. Do not publish.')
        self.reviews = [r for r in self.cfg.get('reviews', []) if r.get('text') and r.get('author') and r.get('source')]
        if len(self.reviews) != len(self.cfg.get('reviews', [])):
            self.warn('site.json', 'reviews without author/text/source were left out (only publish real, attributable reviews)')

    # ---------- helpers ----------
    def c(self, *names):
        return ' '.join(f'{self.p}-{n}' for n in names)

    def err(self, where, msg):
        (self.warnings if self.allow_thin else self.errors).append(f'{where}: {msg}')

    def warn(self, where, msg):
        self.warnings.append(f'{where}: {msg}')

    def content(self, rel, required=True):
        p = os.path.join(self.src, 'content', rel)
        if not os.path.isfile(p):
            if required:
                self.errors.append(f'content/{rel}: missing')
            return {}
        data = json.load(open(p))
        blob = json.dumps(data)
        if self.cfg.get('example'):
            blob = re.sub(r'555-01\d\d|\.test\b', '', blob)
        m = PLACEHOLDER.search(blob)
        if m:
            self.errors.append(f'content/{rel}: placeholder text "{m.group(0)}"')
        return data

    def rel(self, url, depth):
        return ('../' * depth) + url.lstrip('/') if url.startswith('/') else url

    # ---------- page shell ----------
    def head(self, page, depth):
        title, desc = page['title'], page['description']
        where = page['url']
        if not page.get('noindex') and not 30 <= len(title) <= 60:
            self.warn(where, f'title is {len(title)} chars (aim for 30-60)')
        if not page.get('noindex') and not 110 <= len(desc) <= 160:
            self.warn(where, f'meta description is {len(desc)} chars (aim for 110-160)')
        canon = self.origin + page['url']
        f = self.d['fonts']
        fams = '&'.join('family=' + x.replace(' ', '+') + ':wght@400;500;600;700;800'
                        for x in dict.fromkeys([f['heading'], f['body']]))
        og_img = self.origin + '/' + (page.get('og_image') or self.cfg.get('og_image') or 'assets/og.png').lstrip('/')
        robots = 'noindex,follow' if page.get('noindex') else 'index,follow,max-image-preview:large'
        up = '../' * depth
        return f'''<!doctype html>
<html lang="{esc(self.cfg.get('language', 'en'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(self.biz['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{self.d['colors']['primary']}">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fams}&display=swap">
<link rel="stylesheet" href="{up}assets/css/site.css">
<script type="application/ld+json">{json.dumps(self.jsonld(page), ensure_ascii=False, separators=(',', ':'))}</script>
</head>'''

    def jsonld(self, page):
        b = self.biz
        bid = self.origin + '/#business'
        biz = {
            '@type': b.get('schema_type') or SCHEMA_TYPES.get(self.cfg['industry'], SCHEMA_TYPES['default']),
            '@id': bid, 'name': b['name'], 'url': self.origin + '/', 'telephone': b['phone'],
            'image': self.origin + '/' + (b.get('logo') or 'assets/og.png').lstrip('/'),
            'priceRange': b.get('price_range', '$$'),
            'areaServed': [{'@type': 'City', 'name': a['name']} for a in self.areas] or None,
            'openingHoursSpecification': [
                {'@type': 'OpeningHoursSpecification', 'dayOfWeek': h['days'], 'opens': h['opens'], 'closes': h['closes']}
                for h in b.get('hours', [])] or None,
            'sameAs': b.get('social') or None,
            'email': b.get('email'),
            'foundingDate': str(b['founded']) if b.get('founded') else None,
        }
        addr = b.get('address')
        if addr and addr.get('street'):
            biz['address'] = {'@type': 'PostalAddress', 'streetAddress': addr['street'], 'addressLocality': addr['city'],
                              'addressRegion': addr.get('region'), 'postalCode': addr.get('postal'),
                              'addressCountry': addr.get('country')}
        elif addr:
            biz['address'] = {'@type': 'PostalAddress', 'addressLocality': addr.get('city'),
                              'addressRegion': addr.get('region'), 'addressCountry': addr.get('country')}
        if b.get('geo'):
            biz['geo'] = {'@type': 'GeoCoordinates', 'latitude': b['geo']['lat'], 'longitude': b['geo']['lng']}
        graph = [{k: v for k, v in biz.items() if v not in (None, [], '')},
                 {'@type': 'WebSite', '@id': self.origin + '/#website', 'url': self.origin + '/', 'name': b['name'],
                  'publisher': {'@id': bid}},
                 {'@type': 'WebPage', '@id': self.origin + page['url'] + '#webpage', 'url': self.origin + page['url'],
                  'name': page['title'], 'isPartOf': {'@id': self.origin + '/#website'}, 'about': {'@id': bid}}]
        if page.get('crumbs'):
            graph.append({'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': self.origin + u}
                for i, (n, u) in enumerate(page['crumbs'])]})
        if page.get('service'):
            s = page['service']
            graph.append({'@type': 'Service', 'name': s['name'], 'serviceType': s['name'], 'provider': {'@id': bid},
                          'url': self.origin + page['url'], 'description': page['description'],
                          'areaServed': [{'@type': 'City', 'name': a} for a in page.get('area_names', [])] or
                          [{'@type': 'City', 'name': a['name']} for a in self.areas]})
        if page.get('faq'):
            graph.append({'@type': 'FAQPage', 'mainEntity': [
                {'@type': 'Question', 'name': q['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['a']}}
                for q in page['faq']]})
        return {'@context': 'https://schema.org', '@graph': graph}

    def header(self, depth, active):
        up = '../' * depth
        b = self.biz
        v = self.d['variants']['header']
        links = [('Services', 'services/'), ('Service Areas', 'service-areas/')]
        if self.cfg.get('pricing'):
            links.append(('Pricing', '#pricing' if depth == 0 else up + '#pricing'))
        links += [('About', 'about/'), ('Contact', 'contact/')]
        nav = ''.join(
            f'<li><a href="{h if h.startswith(("#", "../")) else up + h}"'
            f'{" aria-current=page" if active == h else ""}>{esc(t)}</a></li>' for t, h in links)
        logo = (f'<img src="{up}{esc(b["logo"])}" alt="{esc(b["name"])}" width="{b.get("logo_width", 180)}" '
                f'height="{b.get("logo_height", 48)}">' if b.get('logo') else
                f'<span class="{self.c("logo-mark")}">{esc(initials(b["name"]))}</span><span class="{self.c("logo-text")}">{esc(b["name"])}</span>')
        phone = f'<a class="{self.c("btn", "btn-accent")}" href="tel:{tel(b["phone"])}" aria-label="Call {esc(b["phone_display"])}">{icon("phone", 18)}<span>{esc(b["phone_display"])}</span></a>'
        top = ''
        if v == 'topbar':
            hours = b.get('hours_text', '')
            top = (f'<div class="{self.c("topbar")}"><div class="{self.c("wrap", "topbar-in")}">'
                   f'<span>{icon("pin", 16)} {esc(b.get("tagline_area", ""))}</span>'
                   f'{"<span>" + icon("clock", 16) + " " + esc(hours) + "</span>" if hours else ""}</div></div>')
        return f'''<a class="{self.c('skip')}" href="#main">Skip to content</a>
<header class="{self.c('header', 'header--' + v)}">{top}
<div class="{self.c('wrap', 'header-in')}">
<a class="{self.c('logo')}" href="{up or './'}">{logo}</a>
<nav class="{self.c('nav')}" aria-label="Main"><ul id="{self.p}-menu">{nav}</ul></nav>
<div class="{self.c('header-cta')}">{phone}<button class="{self.c('menu-btn')}" aria-expanded="false" aria-controls="{self.p}-menu" aria-label="Menu">{icon('menu', 22)}</button></div>
</div></header>'''

    def footer(self, depth):
        up = '../' * depth
        b = self.biz
        v = self.d['variants']['footer']
        svc = ''.join(f'<li><a href="{up}services/{s["slug"]}/">{esc(s["name"])}</a></li>' for s in self.services)
        areas = ''.join(f'<li><a href="{up}service-areas/{a["slug"]}/">{esc(a["name"])}</a></li>' for a in self.area_pages)
        hours = ''.join(f'<li><span>{esc(h["label"])}</span><span>{esc(h["text"])}</span></li>' for h in b.get('hours_display', []))
        addr = b.get('address') or {}
        addr_line = ', '.join(x for x in [addr.get('street'), addr.get('city'), addr.get('region'), addr.get('postal')] if x)
        year = datetime.date.today().year
        cols = f'''<div><p class="{self.c('foot-brand')}">{esc(b['name'])}</p><p>{esc(b.get('footer_blurb', ''))}</p>
<p><a href="tel:{tel(b['phone'])}">{esc(b['phone_display'])}</a>{'<br><a href="mailto:' + esc(b['email']) + '">' + esc(b['email']) + '</a>' if b.get('email') else ''}{'<br>' + esc(addr_line) if addr_line else ''}</p>
{('<p>' + esc(b['license']) + '</p>') if b.get('license') else ''}</div>
<div><p class="{self.c('foot-h')}">Services</p><ul>{svc}</ul></div>
{f'<div><p class="{self.c("foot-h")}">Areas</p><ul>{areas}<li><a href="{up}service-areas/">All areas</a></li></ul></div>' if v == 'columns' else ''}
{f'<div><p class="{self.c("foot-h")}">Hours</p><ul class="{self.c("hours")}">{hours}</ul></div>' if hours else ''}'''
        return f'''<footer class="{self.c('footer', 'footer--' + v)}"><div class="{self.c('wrap', 'foot-grid')}">{cols}</div>
<div class="{self.c('wrap', 'foot-legal')}"><span>&copy; {year} {esc(b.get('legal_name') or b['name'])}</span><a href="{up}privacy-policy/">Privacy Policy</a></div></footer>
<div class="{self.c('mobile-bar')}"><a class="{self.c('btn', 'btn-accent')}" href="tel:{tel(b['phone'])}">{icon('phone', 18)} Call</a><a class="{self.c('btn', 'btn-primary')}" href="{up}contact/">Free Quote</a></div>
<script src="{up}assets/js/site.js" defer></script>'''

    def page(self, page, body, depth=None):
        depth = page['url'].strip('/').count('/') + (1 if page['url'] != '/' else 0) if depth is None else depth
        active = page['url'].strip('/').split('/')[0] + '/' if page['url'] != '/' else ''
        doc = (self.head(page, depth) + f'\n<body class="{self.p}-rhythm-{self.d["layout"]["section_rhythm"]}">\n' + self.header(depth, active) +
               f'\n<main id="main">{body}</main>\n' + self.footer(depth) + '\n</body>\n</html>\n')
        path = os.path.join(self.out, page['url'].strip('/'), 'index.html') if page['url'] != '/404' else os.path.join(self.out, '404.html')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').write(doc)
        self.pages.append(page)

    # ---------- reusable sections ----------
    def crumbs_html(self, crumbs, depth):
        up = '../' * depth
        items = []
        for i, (name, url) in enumerate(crumbs):
            if i == len(crumbs) - 1:
                items.append(f'<li aria-current="page">{esc(name)}</li>')
            else:
                items.append(f'<li><a href="{up}{url.lstrip("/") or "./"}">{esc(name)}</a></li>')
        return f'<nav class="{self.c("crumbs")}" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>'

    def img(self, image, depth, cls, eager=False, w=1200, h=800):
        up = '../' * depth
        if image and image.get('src'):
            return (f'<img class="{self.c(cls)}" src="{up}{esc(image["src"])}" alt="{esc(image.get("alt", ""))}" '
                    f'width="{image.get("width", w)}" height="{image.get("height", h)}"'
                    f'{" fetchpriority=high" if eager else " loading=lazy decoding=async"}>')
        return f'<div class="{self.c(cls, "art")}" aria-hidden="true"></div>'

    def sections(self, secs, depth, where):
        out = []
        for s in secs:
            t = s.get('type', 'text')
            h2 = f'<h2>{esc(s["heading"])}</h2>' if s.get('heading') else ''
            if t == 'text':
                out.append(f'<section class="{self.c("prose")}">{h2}{s["html"]}</section>')
            elif t == 'list':
                lis = ''.join(f'<li>{icon("check", 18)}<span>{x}</span></li>' for x in s['items'])
                out.append(f'<section class="{self.c("prose")}">{h2}{s.get("intro_html", "")}<ul class="{self.c("checks")}">{lis}</ul></section>')
            elif t == 'steps':
                lis = ''.join(f'<li><strong>{esc(x["title"])}</strong><p>{esc(x["text"])}</p></li>' for x in s['items'])
                out.append(f'<section class="{self.c("prose")}">{h2}<ol class="{self.c("steps-list")}">{lis}</ol></section>')
            elif t == 'faq':
                out.append(f'<section class="{self.c("prose")}">{h2}{self.faq_items(s["items"])}</section>')
            elif t == 'table':
                head = ''.join(f'<th scope="col">{esc(x)}</th>' for x in s['columns'])
                rows = ''.join('<tr>' + ''.join(f'<td>{esc(x)}</td>' for x in r) + '</tr>' for r in s['rows'])
                out.append(f'<section class="{self.c("prose")}">{h2}<div class="{self.c("table-wrap")}"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>{s.get("note_html", "")}</section>')
            else:
                self.warn(where, f'unknown section type {t}')
        return ''.join(out)

    def faq_items(self, items):
        return ''.join(f'<details class="{self.c("faq-item")}"><summary>{esc(q["q"])}{icon("chev", 18)}</summary><div>{q["a"] if "<" in q["a"] else "<p>" + esc(q["a"]) + "</p>"}</div></details>' for q in items)

    def quote_form(self, depth, heading='Request a free quote', source='Contact page'):
        opts = ''.join(f'<option>{esc(s["name"])}</option>' for s in self.services)
        f = self.cfg.get('form', {})
        return f'''<form class="{self.c('form')}" data-endpoint="{esc(f.get('endpoint', ''))}" data-thanks="{esc(self.rel(f.get('thank_you', '/thank-you/'), depth))}" novalidate>
<p class="{self.c('form-h')}">{esc(heading)}</p>
<input type="hidden" name="source" value="{esc(source)}">
<div class="{self.c('hp')}" aria-hidden="true"><label>Leave empty<input name="company_website" tabindex="-1" autocomplete="off"></label></div>
<label>Name<input name="name" autocomplete="name" required></label>
<div class="{self.c('form-row')}"><label>Phone<input name="phone" type="tel" autocomplete="tel" required></label>
<label>Email<input name="email" type="email" autocomplete="email"></label></div>
<label>Service<select name="service"><option value="">Choose a service</option>{opts}<option>Something else</option></select></label>
<label>Details<textarea name="message" rows="4"></textarea></label>
<button class="{self.c('btn', 'btn-primary', 'btn-block')}" type="submit">Send request</button>
<p class="{self.c('form-note')}" role="status"></p></form>'''

    # ---------- homepage ----------
    def build_home(self):
        c = self.content('home.json')
        if not c:
            return
        v = self.d['variants']
        b = self.biz
        parts = {}
        hero = c['hero']
        points = ''.join(f'<li>{icon("check", 18)}{esc(x)}</li>' for x in hero.get('points', []))
        ctas = (f'<div class="{self.c("cta-row")}"><a class="{self.c("btn", "btn-accent", "btn-lg")}" href="contact/">{esc(hero.get("cta", "Get a free quote"))}</a>'
                f'<a class="{self.c("btn", "btn-ghost", "btn-lg")}" href="tel:{tel(b["phone"])}">{icon("phone", 18)} {esc(b["phone_display"])}</a></div>')
        text = (f'<div class="{self.c("hero-text")}"><p class="{self.c("eyebrow")}">{esc(hero.get("eyebrow", ""))}</p>'
                f'<h1>{esc(hero["h1"])}</h1><p class="{self.c("lead")}">{esc(hero["lead"])}</p>'
                f'<ul class="{self.c("hero-points")}">{points}</ul>{ctas}</div>')
        if v['hero'] == 'form':
            side = f'<div class="{self.c("hero-side")}">{self.quote_form(0, "Get your free quote", "Homepage hero")}</div>'
        else:
            side = f'<div class="{self.c("hero-side")}">{self.img(hero.get("image"), 0, "hero-img", eager=True)}</div>'
        parts['hero'] = f'<section class="{self.c("hero", "hero--" + v["hero"])}"><div class="{self.c("wrap", "hero-in")}">{text}{side}</div></section>'
        trust = ''.join(f'<li>{icon(x.get("icon", "shield"), 22)}<div><strong>{esc(x["title"])}</strong><span>{esc(x["text"])}</span></div></li>' for x in c.get('trust', []))
        parts['trust'] = f'<section class="{self.c("trust")}" aria-label="Why customers choose us"><ul class="{self.c("wrap", "trust-in")}">{trust}</ul></section>' if trust else ''
        parts['services'] = self.services_block(c.get('services', {}), 0, v['services'])
        parts['pricing'] = self.pricing_block(c.get('pricing', {})) if self.cfg.get('pricing') else ''
        why = c.get('why')
        if why:
            pts = ''.join(f'<li><strong>{esc(x["title"])}</strong><p>{esc(x["text"])}</p></li>' for x in why.get('points', []))
            img = self.img(why.get('image'), 0, 'why-img') if v['why'] == 'split' else ''
            parts['why'] = (f'<section class="{self.c("section", "why", "why--" + v["why"])}"><div class="{self.c("wrap", "why-in")}">{img}'
                            f'<div><h2>{esc(why["heading"])}</h2>{why.get("html", "")}<ul class="{self.c("why-points")}">{pts}</ul></div></div></section>')
        proc = c.get('process')
        if proc:
            steps = ''.join(f'<li><span class="{self.c("step-n")}">{i + 1}</span><strong>{esc(x["title"])}</strong><p>{esc(x["text"])}</p></li>' for i, x in enumerate(proc['steps']))
            parts['process'] = f'<section class="{self.c("section", "process", "process--" + v["process"])}"><div class="{self.c("wrap")}"><h2>{esc(proc["heading"])}</h2><ol class="{self.c("process-list")}">{steps}</ol></div></section>'
        parts['reviews'] = self.reviews_block(c.get('reviews', {}), v['reviews'])
        faq = c.get('faq')
        if faq:
            parts['faq'] = f'<section class="{self.c("section", "faq", "faq--" + v["faq"])}"><div class="{self.c("wrap")}"><h2>{esc(faq["heading"])}</h2><div class="{self.c("faq-list")}">{self.faq_items(faq["items"])}</div></div></section>'
        parts['areas'] = self.areas_block(c.get('areas', {}), 0, v['areas'])
        cta = c.get('cta', {})
        parts['cta'] = (f'<section class="{self.c("cta", "cta--" + v["cta"])}"><div class="{self.c("wrap", "cta-in")}"><div><h2>{esc(cta.get("heading", ""))}</h2><p>{esc(cta.get("lead", ""))}</p></div>'
                        f'<div class="{self.c("cta-row")}"><a class="{self.c("btn", "btn-accent", "btn-lg")}" href="contact/">Get a quote</a><a class="{self.c("btn", "btn-ghost-light", "btn-lg")}" href="tel:{tel(b["phone"])}">{esc(b["phone_display"])}</a></div></div></section>') if cta else ''
        con = c.get('contact', {})
        parts['contact'] = (f'<section class="{self.c("section", "contact-band")}" id="quote"><div class="{self.c("wrap", "contact-in")}"><div><h2>{esc(con.get("heading", "Get in touch"))}</h2><p>{esc(con.get("lead", ""))}</p>{self.contact_facts()}</div>'
                            f'{self.quote_form(0, "Request a free quote", "Homepage contact")}</div></section>') if v['hero'] != 'form' or con else ''
        body = ''.join(parts.get(k, '') for k in self.d['home_order'])
        n = words(body)
        if n < MIN_WORDS['home']:
            self.err('/', f'homepage has {n} words (minimum {MIN_WORDS["home"]})')
        self.page({'url': '/', 'title': c['title'], 'description': c['description'], 'faq': (faq or {}).get('items')}, body, 0)

    def contact_facts(self):
        b = self.biz
        rows = [('phone', f'<a href="tel:{tel(b["phone"])}">{esc(b["phone_display"])}</a>')]
        if b.get('email'):
            rows.append(('mail', f'<a href="mailto:{esc(b["email"])}">{esc(b["email"])}</a>'))
        if b.get('hours_text'):
            rows.append(('clock', esc(b['hours_text'])))
        if b.get('tagline_area'):
            rows.append(('pin', esc(b['tagline_area'])))
        return f'<ul class="{self.c("facts")}">' + ''.join(f'<li>{icon(i, 20)}<span>{t}</span></li>' for i, t in rows) + '</ul>'

    def services_block(self, intro, depth, variant):
        up = '../' * depth
        items = []
        for s in self.services:
            link = f'{up}services/{s["slug"]}/'
            if variant == 'cards':
                items.append(f'<li><a href="{link}">{self.img(s.get("image"), depth, "svc-img", w=600, h=400)}<strong>{esc(s["name"])}</strong><p>{esc(s["short"])}</p><span class="{self.c("more")}">Learn more {icon("arrow", 16)}</span></a></li>')
            elif variant == 'rows':
                items.append(f'<li><div><strong>{esc(s["name"])}</strong><p>{esc(s["short"])}</p></div><a class="{self.c("btn", "btn-primary")}" href="{link}">Details</a></li>')
            else:
                items.append(f'<li>{icon("tool", 22)}<div><a href="{link}"><strong>{esc(s["name"])}</strong></a><p>{esc(s["short"])}</p></div></li>')
        return (f'<section class="{self.c("section", "services", "services--" + variant)}"><div class="{self.c("wrap")}">'
                f'<h2>{esc(intro.get("heading", "Our services"))}</h2>{"<p class=" + chr(34) + self.c("lead") + chr(34) + ">" + esc(intro["lead"]) + "</p>" if intro.get("lead") else ""}'
                f'<ul class="{self.c("svc-list")}">{"".join(items)}</ul></div></section>')

    def areas_block(self, intro, depth, variant):
        if not self.areas:
            return ''
        up = '../' * depth
        pages = {a['slug'] for a in self.area_pages}
        lis = ''.join(f'<li>{icon("pin", 16)}' + (f'<a href="{up}service-areas/{a["slug"]}/">{esc(a["name"])}</a>' if a['slug'] in pages else esc(a['name'])) + '</li>' for a in self.areas)
        return (f'<section class="{self.c("section", "areas", "areas--" + variant)}"><div class="{self.c("wrap")}">'
                f'<h2>{esc(intro.get("heading", "Areas we serve"))}</h2>{"<p class=" + chr(34) + self.c("lead") + chr(34) + ">" + esc(intro["lead"]) + "</p>" if intro.get("lead") else ""}'
                f'<ul class="{self.c("area-list")}">{lis}</ul></div></section>')

    def reviews_block(self, intro, variant):
        if not self.reviews:
            return ''
        cards = ''.join(
            f'<figure class="{self.c("review")}"><div class="{self.c("stars")}" role="img" aria-label="{r.get("rating", 5)} out of 5 stars">{icon("star", 16) * int(r.get("rating", 5))}</div>'
            f'<blockquote>{esc(r["text"])}</blockquote><figcaption><strong>{esc(r["author"])}</strong>'
            f'<span>{esc(", ".join(x for x in [r.get("area"), r.get("source")] if x))}</span></figcaption></figure>'
            for r in self.reviews[:6])
        return f'<section class="{self.c("section", "reviews", "reviews--" + variant)}"><div class="{self.c("wrap")}"><h2>{esc(intro.get("heading", "What customers say"))}</h2><div class="{self.c("review-list")}">{cards}</div></div></section>'

    def pricing_block(self, intro):
        pr = self.cfg['pricing']
        area_region = {}
        for r in pr['regions']:
            for a in r['areas']:
                area_region[a] = r['name']
        missing = [a['name'] for a in self.areas if a['slug'] not in area_region]
        if missing:
            self.errors.append(f'site.json pricing: areas without a region: {", ".join(missing)}')
        cfg = {
            'currency': pr.get('currency', 'CAD'), 'locale': self.cfg.get('language', 'en-CA'),
            'taxRate': pr.get('tax_rate', 0), 'taxLabel': pr.get('tax_label', 'tax'), 'roundTo': pr.get('round_to', 5),
            'jobs': pr['jobs'], 'timing': pr['timing'],
            'services': [{'slug': s['slug'], 'name': s['name'], 'jobs': pr['services'][s['slug']]}
                         for s in self.services if s['slug'] in pr['services']],
            'regions': [{'name': r['name'], 'factor': r['factor'],
                         'areas': [a['name'] for a in self.areas if a['slug'] in r['areas']]} for r in pr['regions']],
            'prefix': self.p,
        }
        return f'''<section class="{self.c('section', 'pricing')}" id="pricing" aria-labelledby="{self.p}-pricing-h"><div class="{self.c('wrap')}">
<h2 id="{self.p}-pricing-h">{esc(intro.get('heading', 'Estimate your price'))}</h2><p class="{self.c('lead')}">{esc(intro.get('lead', ''))}</p>
<div class="{self.c('calc')}" data-calc>
<form class="{self.c('calc-form')}" onsubmit="return false">
<fieldset><legend>Service</legend><div class="{self.c('opts')}" data-calc-group="service"></div></fieldset>
<fieldset><legend>Job type</legend><div class="{self.c('opts')}" data-calc-group="job"></div></fieldset>
<label class="{self.c('calc-label')}">Your area<select data-calc-area></select></label>
<fieldset><legend>Timing</legend><div class="{self.c('opts')}" data-calc-group="timing"></div></fieldset>
</form>
<div class="{self.c('calc-out')}" aria-live="polite"><p class="{self.c('calc-k')}">Estimated price</p><p class="{self.c('calc-title')}" data-out="title"></p>
<p class="{self.c('calc-range')}" data-out="range"></p><p class="{self.c('calc-tax')}" data-out="tax"></p>
<ul class="{self.c('calc-break')}"><li>Base range <b data-out="base"></b></li><li>Area adjustment <b data-out="region"></b></li><li>Timing <b data-out="timing"></b></li></ul>
<a class="{self.c('btn', 'btn-accent', 'btn-block')}" href="contact/" data-calc-book>Book at this estimate</a>
<p class="{self.c('calc-note')}">{esc(pr.get('disclaimer', 'Estimate only. Your final price is confirmed before work begins.'))}</p></div>
</div><script type="application/json" id="{self.p}-pricing">{json.dumps(cfg)}</script></div></section>'''

    # ---------- inner pages ----------
    def build_services(self):
        hub = {'url': '/services/', 'title': f'Services | {self.biz["name"]}', 'description': self.cfg.get('services_hub_description', ''),
               'crumbs': [('Home', '/'), ('Services', '/services/')]}
        if not hub['description']:
            self.errors.append('site.json: services_hub_description missing')
        body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}">{self.crumbs_html(hub["crumbs"], 1)}<h1>{esc(self.cfg.get("services_hub_h1", "Our services"))}</h1></div></section>'
                + self.services_block({}, 1, self.d['variants']['services']))
        self.page(hub, body, 1)
        for s in self.services:
            c = self.content(f'services/{s["slug"]}.json')
            if not c:
                continue
            url = f'/services/{s["slug"]}/'
            crumbs = [('Home', '/'), ('Services', '/services/'), (s['name'], url)]
            faq = [x for sec in c.get('sections', []) if sec.get('type') == 'faq' for x in sec['items']]
            body_sections = self.sections(c.get('sections', []), 2, url)
            n = words(c.get('lead', ''), body_sections)
            if n < MIN_WORDS['service']:
                self.err(url, f'{n} words (minimum {MIN_WORDS["service"]})')
            related = ''.join(f'<li><a href="../{o["slug"]}/">{esc(o["name"])}</a></li>' for o in self.services if o['slug'] != s['slug'])
            body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}">{self.crumbs_html(crumbs, 2)}<h1>{esc(c["h1"])}</h1><p class="{self.c("lead")}">{esc(c["lead"])}</p></div></section>'
                    f'<div class="{self.c("wrap", "page-grid")}"><article class="{self.c("article")}">{self.img(c.get("image"), 2, "page-img")}{body_sections}</article>'
                    f'<aside class="{self.c("sidebar")}">{self.quote_form(2, "Get a quote for " + s["name"], s["name"] + " page")}'
                    f'<div class="{self.c("side-box")}"><p class="{self.c("foot-h")}">Other services</p><ul>{related}</ul></div></aside></div>')
            self.page({'url': url, 'title': c['title'], 'description': c['description'], 'crumbs': crumbs, 'service': s, 'faq': faq}, body, 2)

    def build_areas(self):
        hub_c = self.content('areas.json', required=False)
        hub = {'url': '/service-areas/', 'title': hub_c.get('title', f'Service Areas | {self.biz["name"]}'),
               'description': hub_c.get('description', self.cfg.get('areas_hub_description', '')),
               'crumbs': [('Home', '/'), ('Service Areas', '/service-areas/')]}
        if not hub['description']:
            self.errors.append('content/areas.json or site.json areas_hub_description: description missing')
        body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}">{self.crumbs_html(hub["crumbs"], 1)}<h1>{esc(hub_c.get("h1", "Areas we serve"))}</h1>'
                f'{"<p class=" + chr(34) + self.c("lead") + chr(34) + ">" + esc(hub_c["lead"]) + "</p>" if hub_c.get("lead") else ""}</div></section>'
                + self.areas_block({'heading': hub_c.get('list_heading', 'Communities')}, 1, self.d['variants']['areas'])
                + (f'<div class="{self.c("wrap")}">{self.sections(hub_c.get("sections", []), 1, hub["url"])}</div>' if hub_c.get('sections') else ''))
        self.page(hub, body, 1)
        for a in self.area_pages:
            c = self.content(f'areas/{a["slug"]}.json')
            url = f'/service-areas/{a["slug"]}/'
            crumbs = [('Home', '/'), ('Service Areas', '/service-areas/'), (a['name'], url)]
            if not c.get('local_facts') or len(c['local_facts']) < 3:
                self.err(url, 'needs at least 3 "local_facts" (real, specific details about working in this area)')
            facts = ''.join(f'<li>{icon("pin", 18)}<span>{esc(x)}</span></li>' for x in c.get('local_facts', []))
            body_sections = self.sections(c.get('sections', []), 2, url)
            n = words(c.get('lead', ''), body_sections, ' '.join(c.get('local_facts', [])))
            if n < MIN_WORDS['area']:
                self.err(url, f'{n} words (minimum {MIN_WORDS["area"]})')
            faq = [x for sec in c.get('sections', []) if sec.get('type') == 'faq' for x in sec['items']]
            svc = ''.join(f'<li><a href="../../services/{s["slug"]}/">{esc(s["name"])} in {esc(a["name"])}</a></li>' for s in self.services)
            body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}">{self.crumbs_html(crumbs, 2)}<h1>{esc(c["h1"])}</h1><p class="{self.c("lead")}">{esc(c["lead"])}</p></div></section>'
                    f'<div class="{self.c("wrap", "page-grid")}"><article class="{self.c("article")}">'
                    f'<section class="{self.c("prose")}"><h2>{esc(c.get("facts_heading", "Working in " + a["name"]))}</h2><ul class="{self.c("checks")}">{facts}</ul></section>{body_sections}</article>'
                    f'<aside class="{self.c("sidebar")}">{self.quote_form(2, "Get a quote in " + a["name"], a["name"] + " page")}<div class="{self.c("side-box")}"><p class="{self.c("foot-h")}">Services in {esc(a["name"])}</p><ul>{svc}</ul></div></aside></div>')
            self.page({'url': url, 'title': c['title'], 'description': c['description'], 'crumbs': crumbs, 'faq': faq,
                       'area_names': [a['name']]}, body, 2)

    def build_simple(self, slug, kind, min_words=None, form=False, noindex=False, default=None):
        c = self.content(f'{slug}.json', required=default is None) or default
        if not c:
            return
        url = f'/{c.get("slug", slug)}/'
        crumbs = [('Home', '/'), (c['h1'], url)]
        secs = self.sections(c.get('sections', []), 1, url)
        if min_words and words(c.get('lead', ''), secs) < min_words:
            self.err(url, f'{words(c.get("lead", ""), secs)} words (minimum {min_words})')
        side = (f'<aside class="{self.c("sidebar")}">{self.quote_form(1)}<div class="{self.c("side-box")}">{self.contact_facts()}</div></aside>' if form else '')
        body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}">{self.crumbs_html(crumbs, 1)}<h1>{esc(c["h1"])}</h1>'
                f'{"<p class=" + chr(34) + self.c("lead") + chr(34) + ">" + esc(c["lead"]) + "</p>" if c.get("lead") else ""}</div></section>'
                f'<div class="{self.c("wrap", "page-grid" if form else "page-narrow")}"><article class="{self.c("article")}">{secs}</article>{side}</div>')
        self.page({'url': url, 'title': c['title'], 'description': c['description'], 'crumbs': crumbs, 'noindex': noindex}, body, 1)

    def build_utility(self):
        b = self.biz
        self.build_simple('thank-you', 'utility', noindex=True, default={
            'slug': 'thank-you', 'h1': 'Thank you', 'title': f'Thank You | {b["name"]}',
            'description': f'Thanks for contacting {b["name"]}. We have your request and will call you back shortly to confirm the details.',
            'lead': f'We have your request. If it is urgent, call us now at {b["phone_display"]}.', 'sections': []})
        self.build_simple('privacy-policy', 'utility', noindex=True, default=privacy_default(b))
        nf = {'url': '/404', 'title': f'Page Not Found | {b["name"]}', 'description': 'This page does not exist.', 'noindex': True}
        body = (f'<section class="{self.c("page-head")}"><div class="{self.c("wrap")}"><h1>Page not found</h1>'
                f'<p class="{self.c("lead")}">That page doesn\'t exist. Try our <a href="/services/">services</a> or call <a href="tel:{tel(b["phone"])}">{esc(b["phone_display"])}</a>.</p></div></section>')
        self.page(nf, body, 0)

    # ---------- assets ----------
    def write_assets(self):
        os.makedirs(os.path.join(self.out, 'assets/css'), exist_ok=True)
        os.makedirs(os.path.join(self.out, 'assets/js'), exist_ok=True)
        src_assets = os.path.join(self.src, 'assets')
        if os.path.isdir(src_assets):
            shutil.copytree(src_assets, os.path.join(self.out, 'assets'), dirs_exist_ok=True)
        css = open(os.path.join(HERE, '..', 'templates', 'site.css')).read()
        open(os.path.join(self.out, 'assets/css/site.css'), 'w').write(tokens_css(self.d) + css.replace('__', self.p + '-'))
        js = open(os.path.join(HERE, '..', 'templates', 'site.js')).read().replace('__P__', self.p)
        open(os.path.join(self.out, 'assets/js/site.js'), 'w').write(js)
        col = self.d['colors']
        open(os.path.join(self.out, 'assets/favicon.svg'), 'w').write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="{min(self.d["shape"]["radius"] * 2, 32)}" fill="{col["primary"]}"/>'
            f'<text x="32" y="42" text-anchor="middle" font-family="Arial,sans-serif" font-size="28" font-weight="700" fill="#fff">{esc(initials(self.biz["name"]))}</text></svg>')
        if not os.path.isfile(os.path.join(self.out, 'assets/og.png')):
            self.warn('assets', 'no assets/og.png (1200x630 share image) – add one for social previews')

    def write_sitemap(self):
        today = datetime.date.today().isoformat()
        urls = [p['url'] for p in self.pages if not p.get('noindex') and p['url'] != '/404']
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        xml += [f'<url><loc>{self.origin}{u}</loc><lastmod>{today}</lastmod></url>' for u in sorted(urls, key=lambda u: (u.count('/'), u))]
        xml.append('</urlset>')
        open(os.path.join(self.out, 'sitemap.xml'), 'w').write('\n'.join(xml) + '\n')
        open(os.path.join(self.out, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /thank-you/\n\nSitemap: {self.origin}/sitemap.xml\n')

    def check_duplicates(self):
        seen = {}
        for p in self.pages:
            if p.get('noindex'):
                continue
            for k in ('title', 'description'):
                v = p[k].strip().lower()
                if (k, v) in seen:
                    self.errors.append(f'{p["url"]}: duplicate {k} with {seen[(k, v)]}')
                seen[(k, v)] = p['url']

    def build(self):
        if os.path.isdir(self.out):
            shutil.rmtree(self.out)
        os.makedirs(self.out)
        for s in self.services:
            if not s.get('short'):
                self.errors.append(f'site.json service {s["slug"]}: "short" description missing')
        self.write_assets()
        self.build_home()
        self.build_services()
        self.build_areas()
        self.build_simple('about', 'about', min_words=MIN_WORDS['about'])
        self.build_simple('contact', 'contact', form=True)
        self.build_utility()
        self.check_duplicates()
        self.write_sitemap()
        return self


def tokens_css(d):
    c, f, s, l = d['colors'], d['fonts'], d['shape'], d['layout']
    pad = {'compact': 56, 'regular': 80, 'airy': 108}[l['density']]
    shadow = {'none': 'none', 'soft': '0 10px 30px rgba(10,20,40,.08)', 'lifted': '0 18px 40px -12px rgba(10,20,40,.25)',
              'hard': f'6px 6px 0 {c["dark"]}'}[s['shadow']]
    sc, base = f['scale'], f['base_px']
    return (f':root{{--primary:{c["primary"]};--accent:{c["accent"]};--dark:{c["dark"]};--ink:{c["ink"]};--muted:{c["muted"]};'
            f'--soft:{c["soft"]};--line:{c["line"]};--radius:{s["radius"]}px;--btn-radius:{999 if s["style"] == "pill" else s["radius"]}px;'
            f'--shadow:{shadow};--border:{s["border_px"]}px;--container:{l["container"]}px;--pad:{pad}px;'
            f'--font-h:"{f["heading"]}",system-ui,sans-serif;--font-b:"{f["body"]}",system-ui,sans-serif;--hw:{f["heading_weight"]};'
            f'--hcase:{f["heading_case"]};--htrack:{f["heading_tracking"]};--base:{base}px;'
            f'--h1:{round(base * sc ** 5)}px;--h2:{round(base * sc ** 3.6)}px;--h3:{round(base * sc ** 1.6)}px;'
            f'--band:{"var(--dark)" if l["section_rhythm"] == "bold-bands" else "var(--soft)"};'
            f'--band-ink:{"#fff" if l["section_rhythm"] == "bold-bands" else "var(--ink)"}}}\n')


def initials(name):
    w = [x for x in re.findall(r'[A-Za-z]+', name) if x.lower() not in ('and', 'the', 'of', 'inc', 'ltd')]
    return ''.join(x[0] for x in w[:2]).upper() or name[:1].upper()


def tel(phone):
    return re.sub(r'[^\d+]', '', phone)


def privacy_default(b):
    name = b['name']
    return {'slug': 'privacy-policy', 'h1': 'Privacy Policy', 'title': f'Privacy Policy | {name}',
            'description': f'How {name} collects, uses and protects the information you share through this website, forms and phone calls.',
            'sections': [{'type': 'text', 'html':
                          f'<p>{esc(name)} collects the details you send us through this website (name, phone, email, address and message) '
                          f'only to respond to your request, schedule service and keep records of work we do for you.</p>'
                          '<p>We do not sell your information. We share it only with service providers who help us run the business '
                          '(for example, our form or email provider), and only as needed.</p>'
                          f'<p>To see, correct or delete the information we hold about you, contact us at {esc(b.get("email") or b["phone_display"])}.</p>'
                          '<p class="note">Have this policy reviewed for your jurisdiction before publishing.</p>'}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site_dir')
    ap.add_argument('--out')
    ap.add_argument('--allow-thin', action='store_true')
    a = ap.parse_args()
    out = a.out or os.path.join(a.site_dir, 'dist')
    s = Site(a.site_dir, out, a.allow_thin).build()
    for w in s.warnings:
        print('warning:', w)
    for e in s.errors:
        print('ERROR:', e)
    print(f'{len(s.pages)} pages -> {out} ({len(s.errors)} errors, {len(s.warnings)} warnings)')
    sys.exit(1 if s.errors else 0)


if __name__ == '__main__':
    main()
