# Technical SEO

## Handled by build_site.py

- One `<h1>` per page; logical H2/H3 structure
- Unique `<title>` and meta description per page (the build fails on duplicates; warns outside 30–60 / 110–160 chars)
- Absolute `rel=canonical` on every page; `og:url` = canonical
- Open Graph + Twitter card tags (`og:image` from `assets/og.png` or per page `og_image`)
- `robots` meta: `index,follow` normally, `noindex,follow` on thank-you, privacy and 404
- JSON-LD `@graph`: LocalBusiness subtype (from industry), WebSite, WebPage, BreadcrumbList; Service on service
  pages; FAQPage where FAQs exist. No self-serving AggregateRating (Google ignores it for LocalBusiness and it
  invites manual review)
- `sitemap.xml` (only indexable pages) and `robots.txt` with the sitemap URL
- Breadcrumb navigation that matches the BreadcrumbList
- Images: `width`/`height` attributes, `loading=lazy` + `decoding=async` below the fold, `fetchpriority=high` on
  the hero
- Performance: one CSS file, one deferred JS file, no frameworks, Google Fonts with `display=swap`, SVG favicon
- Accessibility: skip link, labelled form fields, focus styles, `aria-live` on the calculator, reduced-motion
  support, AA-contrast primary colour (design_seed checks it)
- Mobile: responsive layout, sticky call / quote bar on small screens, 48px tap targets
- Real 404 page

## Before launch

- [ ] `build_site.py` has 0 errors; warnings reviewed
- [ ] `uniqueness_check.py` passes against all other sites in the portfolio
- [ ] `seo_audit.py --site-url <domain>` shows no `high` issues
- [ ] Lighthouse mobile on home + one service page: Performance ≥ 90, SEO 100, Accessibility ≥ 95
- [ ] Real photos in place (compressed WebP, ≤ 200 KB each, real alt text) and `assets/og.png` (1200×630)
- [ ] Form endpoint set and tested end to end (the submission arrives)
- [ ] Prices in the calculator confirmed by the business
- [ ] Privacy policy reviewed for the jurisdiction
- [ ] Host serves gzip/brotli, long cache headers for `/assets/`, HTTPS, and one canonical host (redirect
      `http://` and the non-preferred `www`/apex variant)

## After launch

- [ ] Verify the domain in Google Search Console and Bing Webmaster Tools; submit `sitemap.xml`
- [ ] Create or claim the Google Business Profile; same name, phone and address (NAP) as the site; link the site
- [ ] List the business on the main directories for the country/trade with identical NAP
- [ ] Ask real customers for reviews on the Google Business Profile (not on the site's own form)
- [ ] Analytics with consent where required (e.g. GA4 or a privacy-friendly alternative); track calls and form
      submissions as conversions
- [ ] Re-run `seo_audit.py` after each content update; check Search Console coverage and Core Web Vitals monthly

## Hosting notes

The `dist/` folder is plain static files with directory-style URLs (`/services/drain-cleaning/` →
`services/drain-cleaning/index.html`). Any static host works. Set the host's 404 page to `/404.html`.
