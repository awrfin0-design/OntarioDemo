---
name: local-service-site-builder
description: Build a complete, SEO-ready website for a local service business (HVAC, plumbing, roofing, electrical, cleaning, landscaping, etc.) from an industry, a region and the business's real details. Produces a unique design system, unique copy, service and area pages, a regional pricing calculator, schema, sitemap and robots.txt, then audits the result and checks it is not a near-duplicate of the other sites you have built. Use when asked to create, scaffold or mass-produce a local business / lead-gen / service-area website, or to add a new site to an existing portfolio.
---

# Local service site builder

Turns **industry + region + real business facts** into a finished static website that can be hosted anywhere
(Netlify, Cloudflare Pages, S3, any web server). Each site gets its own design system and its own copy, and the
build refuses to publish pages that are thin, templated or copied from another site in the portfolio.

## Read this first: what "unique" has to mean

Search engines don't penalise shared code. Millions of sites run the same theme. What gets sites demoted or
removed is **content**:

- *Scaled content abuse*: many pages or sites produced mainly to rank, with little original value.
- *Doorway pages*: the same page repeated per city or keyword ("Furnace Repair Toronto", "Furnace Repair Ottawa"…).
- *Site reputation / duplicate sites*: networks of look-alike sites for the same queries.

So this skill does two separate things:

1. **Visual & code uniqueness** (brand differentiation): `design_seed.py` gives each site its own palette, type
   pairing, shape language, spacing, section variants, homepage order and CSS class prefix.
2. **Content uniqueness** (what actually protects rankings): every page is written for this business and this
   place, built from facts the business supplied or that you researched. `uniqueness_check.py` blocks the
   release if a page overlaps too much with another page on the same site or any page on the other sites.

Do **not** try to defeat duplicate detection by spinning, synonym-swapping or reordering the same text. It
fails the check and it's exactly what search engines' spam policies target. If you can't write something
specific for a page, don't create the page. List the area on the Service Areas page instead.

Never invent business facts: reviews, licence numbers, years in business, addresses, certifications, prices,
or guarantees. If a fact is missing, ask for it or leave that element out (the build omits review sections
when there are no real reviews).

## Inputs

Required from the user (ask in one message if missing):

- Industry and the services offered (3–8 core services)
- Region: the home base and the communities served
- Business name, phone, email, domain
- Address (or confirmation it's a service-area business with no public address), hours
- Real proof points: years in business, licences/insurance, warranties, team size, anything that makes them different
- Real reviews with author and source (optional; never fabricate)
- Prices or price ranges per service if a pricing calculator is wanted (otherwise no calculator)
- Form endpoint (Formspree, Netlify Forms, Basin, own API) or "not yet"

See `references/intake.md` for the full question list and what each answer is used for.

## Workflow

Work in a sites folder (one folder per site, e.g. `sites/<site-slug>/`) so every new site can be checked against
all the existing ones.

1. **Intake.** Collect the inputs above. Write `sites/<slug>/site.json` following `references/site-json.md`
   (copy `examples/harbourview-plumbing/site.json` as a starting point and replace everything).

2. **Research the region** (web search if available). For each community you plan to give its own page, gather
   at least three concrete, checkable local facts relevant to the trade: housing age and type, water hardness,
   climate and weather events, soil, common building codes or permits, drive time from the shop. Note the
   sources. Communities without real local facts go on the Service Areas list only. No page.

3. **Design.** Generate the design, keeping away from existing sites:
   ```bash
   python3 scripts/design_seed.py --industry <industry> --name "<Business>" --domain <domain> \
     --avoid sites/*/design.json --out sites/<slug>/design.json
   ```
   Review the output and, if it doesn't suit the brand (e.g. clashes with a logo), re-run with `--min-distance`
   or edit `design.json` by hand (colours, fonts, variants, `home_order`).

4. **Write the content** into `sites/<slug>/content/` following `references/content-rules.md` and the formats in
   `references/site-json.md`:
   - `home.json`, `about.json`, `contact.json`
   - `services/<slug>.json` for every service in site.json
   - `areas/<slug>.json` only for communities with real local facts
   - optional `areas.json` for the Service Areas hub page
   Write each page from scratch for this business. Don't start from another site's copy, and don't reuse
   paragraphs between pages of this site.

5. **Photos.** Put real photos (team, vans, finished jobs) in `sites/<slug>/assets/img/`, reference them in content
   (`"image": {"src": "assets/img/x.webp", "alt": "...", "width": 1200, "height": 800}`), and add a
   1200×630 `assets/og.png`. Without photos the build uses generated colour art, which is fine for a draft
   but weaker for conversions. Don't use the same stock photos across sites.

6. **Build.**
   ```bash
   python3 scripts/build_site.py sites/<slug>            # writes sites/<slug>/dist
   ```
   Fix every `ERROR` (thin pages, placeholders, missing SEO fields, duplicate titles/descriptions, areas with no
   pricing region). Treat warnings as a to-do list. `--allow-thin` is for drafts only.

7. **Check uniqueness against the whole portfolio.**
   ```bash
   python3 scripts/uniqueness_check.py sites/<slug>/dist --against sites/*/dist
   ```
   (Exclude the site's own dist from `--against`.) If it fails, rewrite the flagged pages. Don't tweak words to
   scrape under the threshold.

8. **Audit.**
   ```bash
   python3 scripts/seo_audit.py sites/<slug>/dist --site-url <domain> --md sites/<slug>/seo-audit.md
   ```
   No `high` issues should remain. If a browser is available, also run Lighthouse (mobile) on the homepage and
   one service page; target Performance ≥ 90, SEO 100, Accessibility ≥ 95.

9. **Test in a browser.** Serve `dist/` (`python3 -m http.server`), click through the menu on desktop and mobile,
   change every calculator option, submit the form (it must reach the endpoint or clearly say it isn't
   connected), and check there's no horizontal scroll on a phone.

10. **Hand over** with the launch checklist in `references/technical-seo.md` (Search Console, sitemap submission,
    Google Business Profile, consistent name/address/phone across listings, form endpoint, analytics).

## What the build produces

- `index.html`: homepage with hero, trust strip, services, pricing calculator (if configured), why-us, process,
  reviews (only if real ones were given), FAQ, service areas, CTA and contact form, in the site's own order.
- `services/` hub and one page per service; `service-areas/` hub and one page per researched community.
- `about/`, `contact/`, `privacy-policy/` (noindex, have it reviewed), `thank-you/` (noindex), `404.html`.
- Per page: unique title and meta description, canonical, Open Graph, one H1, breadcrumbs, JSON-LD
  (LocalBusiness subtype, WebSite, WebPage, BreadcrumbList, Service, FAQPage where relevant).
- `sitemap.xml` (indexable pages only), `robots.txt`, SVG favicon, `assets/css/site.css`, `assets/js/site.js`.
- No frameworks or build tools in the output: fast pages with a small, deferred script.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/design_seed.py` | Deterministic, unique design system per business; `--avoid` keeps distance from existing sites |
| `scripts/build_site.py` | Generates the site from `site.json` + `design.json` + `content/`, enforces quality gates |
| `scripts/uniqueness_check.py` | Text overlap within the site and against other sites, plus design distance; exit 1 on failure |
| `scripts/seo_audit.py` | Works on any static site: titles, descriptions, H1s, canonicals, schema, images, links, thin and near-duplicate content |

Requirements: Python 3.9+, `pip install beautifulsoup4 lxml` (for the checker and audit).

## References

- `references/intake.md`: questions to ask and why
- `references/site-json.md`: `site.json` and content file formats
- `references/content-rules.md`: how to write pages that are useful and unique; page architecture rules
- `references/technical-seo.md`: what the build handles, and the launch checklist
- `examples/harbourview-plumbing/`: complete example input (fictional business, marked `"example": true`)
