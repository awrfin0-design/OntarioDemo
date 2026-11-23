# Ontario Service Pros – homepage duplicate

Static copy of the homepage, section by section, with the original text, layout, styles, images and hero video.

## Run locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Changes from the original

- Google Tag Manager tracking removed.
- Forms no longer post to the original site's lead service. Set `window.FORM_ENDPOINT` (and optionally `window.FORM_THANK_YOU_URL`) near the bottom of `index.html` to connect them to your own form backend. Until then, submissions are only logged to the browser console.
- The search "no results" report in `script.js` is off unless `window.SEARCH_MISS_ENDPOINT` is set.

Links to inner pages (services, brands, cities, contact, etc.) are kept as in the original, but those pages are not included yet.
