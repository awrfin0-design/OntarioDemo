# Ontario Service Pros – full site duplicate

Static copy of the whole site: original text, layout, styles, images and hero video, page by page.

> **Before publishing:** this is a copy of a live website (content, name, phone, reviews). Read
> [`SEO-AUDIT.md`](SEO-AUDIT.md) first. It explains why it can't rank as-is and what to change.

## SEO

- [`SEO-AUDIT.md`](SEO-AUDIT.md): full audit, what was fixed, what's open, recommendations.
- `tools/seo_fix.py`: technical fixes already applied (canonicals, single H1, image sizes and lazy loading,
  broken links, favicon, desktop-only hero video, noindex on utility pages). Safe to re-run.
- `tools/seo_finalize.py --site-url https://your-domain`: run once the domain is known; makes canonical and
  Open Graph URLs absolute and writes `sitemap.xml` + `robots.txt`.
- Re-audit any time: `python3 .claude/skills/local-service-site-builder/scripts/seo_audit.py . --site-url https://your-domain`

## Site builder skill

`.claude/skills/local-service-site-builder/` is a Claude Code skill for building new local-service sites from an
industry, a region and real business details. Each site gets a unique design system and unique content, plus
schema, sitemap and a pricing calculator, and the build checks it against your other sites before launch.
Start with its `SKILL.md`. In Claude Code, just ask, e.g. "build a site for a roofing company in Halifax".

## What's included (3,683 pages)

- Homepage, About, Contact, Services (+ 6 service category pages), Brands, Service Areas, Privacy Policy, Thank You
- All service pages (furnace repair, AC installation, water heater repair, etc.)
- 28 brand pages
- 111 city pages
- Per-city brand pages (e.g. `toronto/brands/`, `acton/jandy--brand/`)

City-service links like `toronto/furnace-repair/` also return 404 on the original site, so they are left as they were.

## Run locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

Use a local server rather than double-clicking the files, so that links between pages (`about/`, `contact/` …) resolve to their `index.html`.

## Site index

`site-index.html` lists and links every page, grouped, with a filter box. It works by double-clicking, without a server.

## Single-file homepage

`dist/ontario-service-pros.html` is the homepage only, with everything (styles, scripts, images, fonts, hero video) built into one file. Open it by double-clicking. Its links to other pages won't work on their own.

## Service pricing calculator (homepage)

The third section of the homepage (`#pricing`, between the service cards and About Us) estimates a price range from four choices: service, job type (repair / maintenance / installation), city and timing (scheduled / same-day / emergency).

- **Edit prices in one place:** the `PRICING` table at the top of `assets/js/pricing-calculator.js`.
  - `services` – base `[low, high]` range per service and job type (CAD, before tax).
  - `regions` – each region's cities and its price factor (`1.10` = +10%). All 111 service-area cities are assigned.
  - `timing` – factor for same-day and emergency service.
  - `taxRate` – used for the "with HST" line.
- **The current numbers are placeholders.** Replace them with real prices before going live.
- **"Book at this estimate"** opens the site's existing Get a Quote pop-up with the estimate pre-filled in the message.
- **Styles:** `assets/css/pricing-calculator.css`.

If you change prices, rebuild `dist/ontario-service-pros.html` (or edit the same `PRICING` table inside it), because the single-file version has its own copy.

## Changes from the original

- Google Tag Manager tracking removed on every page.
- Forms no longer post to the original site's lead service. Set `window.FORM_ENDPOINT` (and optionally `window.FORM_THANK_YOU_URL`) in the small `<script>` block near the bottom of each page to connect them to your own form backend. Until then, submissions are only logged to the browser console.
- The search "no results" report in `script.js` is off unless `window.SEARCH_MISS_ENDPOINT` is set.
