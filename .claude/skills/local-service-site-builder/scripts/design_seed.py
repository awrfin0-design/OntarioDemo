#!/usr/bin/env python3
"""
Generate a unique, deterministic design system for one site.

    python3 design_seed.py --industry hvac --name "Business Name" --domain example.ca [--out design.json]
    python3 design_seed.py ... --avoid other-site/design.json another/design.json

Same name + domain -> same design (re-runnable). Different businesses -> different palette,
type pairing, shape language, density, section variants, section order and CSS class prefix.
--avoid re-rolls until the design differs enough from the listed sites (see design_distance).
"""
import argparse
import colorsys
import hashlib
import json
import random
import string

# Hue ranges (degrees) that suit each industry. A site picks a primary hue inside one range.
INDUSTRY_HUES = {
    'hvac': [(195, 225), (0, 12), (20, 32)],
    'plumbing': [(190, 220), (170, 190), (215, 235)],
    'electrical': [(42, 52), (220, 240), (15, 28)],
    'roofing': [(200, 220), (8, 22), (25, 35), (150, 165)],
    'landscaping': [(95, 140), (140, 165), (30, 40)],
    'cleaning': [(165, 195), (195, 215), (260, 280)],
    'pest-control': [(90, 130), (25, 40), (0, 10)],
    'painting': [(260, 300), (330, 350), (190, 210)],
    'garage-doors': [(205, 225), (0, 12), (30, 40)],
    'appliance-repair': [(200, 225), (150, 170), (0, 10)],
    'pool-spa': [(180, 200), (195, 210)],
    'locksmith': [(40, 52), (210, 230), (0, 10)],
    'moving': [(20, 35), (205, 225), (140, 160)],
    'default': [(0, 360)],
}

FONT_PAIRS = [  # (heading, body) – all on Google Fonts
    ('Barlow Condensed', 'Barlow'), ('Montserrat', 'Source Sans 3'), ('Poppins', 'Inter'),
    ('Oswald', 'Open Sans'), ('Archivo', 'Archivo'), ('Manrope', 'Manrope'), ('Outfit', 'Work Sans'),
    ('Sora', 'Inter'), ('Rubik', 'Rubik'), ('Plus Jakarta Sans', 'Plus Jakarta Sans'),
    ('DM Serif Display', 'DM Sans'), ('Fraunces', 'Inter'), ('Space Grotesk', 'IBM Plex Sans'),
    ('Lexend', 'Lexend'), ('Red Hat Display', 'Red Hat Text'), ('Figtree', 'Figtree'),
    ('Bricolage Grotesque', 'Nunito Sans'), ('Urbanist', 'Karla'), ('Kanit', 'Mulish'),
    ('Libre Franklin', 'Libre Franklin'), ('Saira', 'Lato'), ('Chivo', 'Chivo'),
]

VARIANTS = {
    'header': ['bar', 'centered', 'topbar'],
    'hero': ['split', 'fullbleed', 'form'],
    'services': ['cards', 'rows', 'list'],
    'why': ['split', 'tiles'],
    'process': ['steps', 'timeline'],
    'reviews': ['cards', 'quote'],
    'faq': ['accordion', 'columns'],
    'areas': ['chips', 'columns'],
    'cta': ['band', 'card'],
    'footer': ['columns', 'compact'],
}
# Middle sections of the homepage: the order is shuffled per site, within these rules.
MIDDLE = ['services', 'pricing', 'why', 'process', 'reviews', 'faq', 'areas']
EARLY = {'services', 'pricing'}          # at least one of these in the first two slots
NOT_ADJACENT = {('reviews', 'faq')}       # avoid back-to-back light text blocks


def hsl_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))


def luminance(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tone_for_contrast(h, s, start_l, against='#ffffff', target=4.6):
    l = start_l
    while contrast(hsl_hex(h, s, l), against) < target and l > 0.08:
        l -= 0.02
    return hsl_hex(h, s, l)


def build(industry, name, domain, salt=0):
    seed = int(hashlib.sha256(f'{name}|{domain}|{salt}'.encode()).hexdigest(), 16)
    rnd = random.Random(seed)
    ranges = INDUSTRY_HUES.get(industry, INDUSTRY_HUES['default'])
    lo, hi = rnd.choice(ranges)
    hue = rnd.uniform(lo, hi)
    sat = rnd.uniform(0.55, 0.85)
    scheme = rnd.choice(['complementary', 'split', 'analogous', 'triad'])
    accent_hue = {'complementary': hue + 180, 'split': hue + rnd.choice([150, 210]),
                  'analogous': hue + rnd.choice([-35, 35]), 'triad': hue + rnd.choice([120, 240])}[scheme]
    primary = tone_for_contrast(hue, sat, rnd.uniform(0.38, 0.5))
    accent = tone_for_contrast(accent_hue, rnd.uniform(0.65, 0.9), rnd.uniform(0.45, 0.55), target=4.5)
    dark = hsl_hex(hue, rnd.uniform(0.25, 0.55), rnd.uniform(0.08, 0.14))
    ink = hsl_hex(hue, 0.15, rnd.uniform(0.1, 0.16))
    muted = tone_for_contrast(hue, 0.08, 0.42, target=5.5)
    soft = hsl_hex(hue, rnd.uniform(0.3, 0.6), rnd.uniform(0.955, 0.975))
    line = hsl_hex(hue, 0.2, 0.89)
    heading, body = rnd.choice(FONT_PAIRS)
    shape = rnd.choice(['sharp', 'soft', 'round', 'pill'])
    radius = {'sharp': 2, 'soft': 8, 'round': 14, 'pill': 18}[shape] + rnd.choice([0, 2])
    middle = shuffle_middle(rnd)
    prefix = rnd.choice(string.ascii_lowercase) + ''.join(rnd.choice(string.ascii_lowercase + string.digits) for _ in range(2))
    return {
        'version': 1,
        'industry': industry,
        'seed_input': {'name': name, 'domain': domain, 'salt': salt},
        'colors': {'primary': primary, 'accent': accent, 'dark': dark, 'ink': ink, 'muted': muted,
                   'soft': soft, 'line': line, 'scheme': scheme},
        'fonts': {'heading': heading, 'body': body,
                  'heading_weight': rnd.choice([600, 700, 800]), 'heading_case': rnd.choice(['none', 'none', 'uppercase']),
                  'heading_tracking': rnd.choice(['-0.02em', '-0.01em', '0', '0.01em']),
                  'scale': rnd.choice([1.2, 1.25, 1.3, 1.333]), 'base_px': rnd.choice([16, 17, 18])},
        'shape': {'style': shape, 'radius': radius, 'button': rnd.choice(['solid', 'solid', 'outline-hover', 'shadow']),
                  'shadow': rnd.choice(['none', 'soft', 'lifted', 'hard']), 'border_px': rnd.choice([1, 1, 2])},
        'layout': {'container': rnd.choice([1120, 1180, 1240, 1300]), 'density': rnd.choice(['compact', 'regular', 'airy']),
                   'section_rhythm': rnd.choice(['alternate', 'mostly-light', 'bold-bands'])},
        'variants': {k: rnd.choice(v) for k, v in VARIANTS.items()},
        'home_order': ['hero', 'trust'] + middle + ['cta', 'contact'],
        'class_prefix': prefix,
        'icon_style': rnd.choice(['line', 'solid', 'duotone']),
    }


def shuffle_middle(rnd):
    for _ in range(200):
        order = MIDDLE[:]
        rnd.shuffle(order)
        if not EARLY & set(order[:2]):
            continue
        if any((a, b) in NOT_ADJACENT or (b, a) in NOT_ADJACENT for a, b in zip(order, order[1:])):
            continue
        return order
    return MIDDLE[:]


def design_distance(a, b):
    """0 = identical, 1 = nothing in common."""
    checks = [
        a['colors']['primary'] != b['colors']['primary'] and abs(hue_of(a['colors']['primary']) - hue_of(b['colors']['primary'])) > 18,
        a['fonts']['heading'] != b['fonts']['heading'],
        a['fonts']['body'] != b['fonts']['body'],
        a['shape']['style'] != b['shape']['style'],
        a['layout']['density'] != b['layout']['density'],
        a['home_order'] != b['home_order'],
    ] + [a['variants'][k] != b['variants'][k] for k in VARIANTS]
    return sum(checks) / len(checks)


def hue_of(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    d = h * 360
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--industry', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--domain', required=True)
    ap.add_argument('--avoid', nargs='*', default=[], help='design.json files of existing sites to stay away from')
    ap.add_argument('--min-distance', type=float, default=0.55)
    ap.add_argument('--out', default='design.json')
    a = ap.parse_args()
    others = [json.load(open(p)) for p in a.avoid]
    for salt in range(500):
        d = build(a.industry, a.name, a.domain, salt)
        dists = [design_distance(d, o) for o in others]
        if all(x >= a.min_distance for x in dists):
            break
    json.dump(d, open(a.out, 'w'), indent=2)
    near = f", min distance to {len(others)} other site(s): {min(dists):.2f}" if others else ''
    print(f"design -> {a.out}: {d['fonts']['heading']}/{d['fonts']['body']}, primary {d['colors']['primary']}, "
          f"{d['shape']['style']} shapes, hero={d['variants']['hero']}, prefix={d['class_prefix']}{near}")


if __name__ == '__main__':
    main()
