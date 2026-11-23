# Ontario Service Pros – full site duplicate

Static copy of the whole site: original text, layout, styles, images and hero video, page by page.

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

Then open http://localhost:8000. Use a local server rather than double-clicking the files, so that links between pages (`about/`, `contact/` …) resolve to their `index.html`.

## Single-file homepage

`dist/ontario-service-pros.html` is the homepage only, with everything (styles, scripts, images, fonts, hero video) built into one file. Open it by double-clicking. Its links to other pages won't work on their own.

## Changes from the original

- Google Tag Manager tracking removed on every page.
- Forms no longer post to the original site's lead service. Set `window.FORM_ENDPOINT` (and optionally `window.FORM_THANK_YOU_URL`) in the small `<script>` block near the bottom of each page to connect them to your own form backend. Until then, submissions are only logged to the browser console.
- The search "no results" report in `script.js` is off unless `window.SEARCH_MISS_ENDPOINT` is set.
