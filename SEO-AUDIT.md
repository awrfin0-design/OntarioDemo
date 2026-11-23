# SEO Audit: Ontario Service Pros copy (this repo)

*Audited 23 Nov 2026 · 3,684 pages · tools: `seo_audit.py` (every page), Lighthouse 12 (homepage, mobile)*

## Summary

The technical basics are now in good shape, and the fixable technical issues have been fixed (see "What was
fixed"). The site's real SEO problems are **content and structure**, and no technical change can solve them:

1. **It's a copy of a live website.** Every page duplicates ontarioservicepros.ca, which is already indexed.
   Search engines show the original and filter out copies, so this site can't rank as it stands. It also uses
   that company's name, phone number, reviews and claims ("15+ years", "licensed technicians"), which belong to
   them. **Before this site goes anywhere public, it needs its own business, brand and content.**
2. **95% of pages are near-duplicates of each other** (3,497 of 3,684 are ≥ 80% the same as another page). The
   page structure (every city × every brand, ~200 keyword-variant service pages) is the pattern search
   engines' spam policies call doorway pages / scaled content.
3. **Performance on mobile is poor** (Lighthouse 45, largest content 8.9 s), mainly from the theme's JavaScript.

| | Before | After fixes |
|---|---|---|
| Lighthouse mobile: Performance / Accessibility / Best Practices / SEO | 39 / 87 / 100 / 100 | 45 / 87 / 100 / 92* |
| Homepage download size | 6.5 MB | 2.6 MB |
| Total blocking time | 1,040 ms | 500 ms |
| Pages without a canonical tag | 3,684 | 0 (1 noindex utility page) |
| Pages with two H1s | 118 | 0 |
| Pages linking to missing pages | 222 | 0 |
| Pages with images missing width/height | 3,683 | 0 |
| Near-duplicate pages | 3,497 | 3,497 (needs your decision, below) |

\* SEO drops from 100 to 92 only because canonical URLs must be absolute (`https://yourdomain/...`), which needs
the domain. Run `python3 tools/seo_finalize.py --site-url https://your-domain` and it goes back to 100.

## Critical: content and structure

### 1. Duplicate of an existing site
All text, images, reviews and business details are copied from ontarioservicepros.ca. A copy published on
another domain:
- won't rank (the original is indexed first and is the canonical version),
- can be reported (DMCA / trademark), which gets pages removed from search,
- misleads customers about who they're calling, and uses another business's reviews.

**Fix:** use this build as a design and structure starting point only. Replace the business name, logo,
phone, address and claims with your own, remove the copied reviews, and rewrite the copy. The skill in
`.claude/skills/local-service-site-builder/` does this with fresh content and a uniqueness check.

### 2. Doorway-style page structure

| Page group | Pages | How alike | Example |
|---|---|---|---|
| City × brand pages | 3,219 | 86–96% identical | `/toronto/napoleon--brand/` vs `/london/napoleon--brand/` |
| City hub pages (`/<city>/`, `/<city>/brands/`, `/<city>/services/`) | 333 | 85% identical | `/guelph/` vs `/hamilton/` |
| Keyword-variant service pages | ~200 | different wording, same search intent | `fix-my-fireplace`, `fireplace-fixing`, `fireplace-repairman`, `fix-gas-fireplace`, `pool-heaters-repaire` (misspelt) |
| Brand page pairs | 28 pairs | 100% identical | `/napoleon--brand/` = `/napoleon--gas-fireplace-repair/` |

Thousands of near-identical pages split ranking signals, waste crawl budget, and can trigger a site-wide
quality downgrade, which hurts the good pages too.

**Recommendation (your call):**
- Keep **one page per real service** (about 6–12), each covering its keyword variants. 301-redirect the
  ~200 variant URLs to the matching service page.
- Keep brand pages only for brands you genuinely install or are authorised for; one page each (the 28
  duplicate URLs already point their canonical at the `--brand` page).
- Keep **city pages only where you can write something specific** (local housing stock, water, travel time,
  real jobs done there). Probably 5–15 cities, not 111. List the rest on the Service Areas page.
- Remove the city × brand pages (redirect to the brand page) or set them to `noindex`.

I haven't deleted or redirected anything: it removes thousands of URLs, and which pages to keep depends on
the real business behind the site.

### 3. Reviews and trust claims
8 named reviews on the homepage, with no source (Google, HomeStars...), copied from the original site.
"15+ Years in Service", "certified technicians", "licensed and insured" are claims about that business.
Replace with your own verifiable reviews (link to the Google Business Profile) and your own facts.

## Technical: fixed

Script: `tools/seo_fix.py` (re-runnable, edits markup in place)

- **Canonical tags** on every page. The 28 duplicate brand URLs point at their `--brand` twin.
- **One H1 per page**: the second H1 ("Gas Running But Something's Off?...") became an H2 with identical styling.
- **Image width/height** on all images (prevents layout shift); `loading=lazy` + `decoding=async` below the first section.
- **222 pages with broken links** (`/acton/furnace-repair/` etc., which are 404 on the original too) now
  link to the real service page (`/furnace-repair/`).
- **Favicon**: the 519 KB PNG loaded as the icon on every page was replaced with 32/180/192 px icons.
- **Hero video**: the 3.2 MB background video now loads only on screens ≥ 992 px wide; phones get the poster
  image (preloaded). Desktop is unchanged.
- **noindex** on `/thank-you/` and `site-index.html` (still followed).

## Technical: needs the domain

Script: `tools/seo_finalize.py --site-url https://your-domain`
- Makes canonical, `og:url`, `og:image` and structured-data URLs absolute
- Writes `sitemap.xml` (indexable, self-canonical pages only) and `robots.txt`

Tested on a copy; not run here because there's no domain yet.

## Technical: still open

| Issue | Impact | Recommendation |
|---|---|---|
| Theme JavaScript: `vendor.js` (432 KB, ~2.8 s of mobile CPU), Vue + an 815 KB search index (`script.js`) on every page | Slow interactivity, LCP 8.9 s on mobile | Load the search index only when search is opened; drop unused jQuery plugins; or rebuild on the lighter skill template (Lighthouse 93 mobile) |
| 20 separate CSS files, ~430 KB unused CSS | Render delay | Combine and purge unused rules |
| HTML ~134 KB per page (2,564 DOM nodes on home) | Slower parsing | Mostly the 111-city list and brand grid repeated on every page. Show them on hub pages only |
| 1,626 titles over 60 characters | Truncated in results | Shorten: `Service in City \| Brand` |
| 58 duplicate titles / 66 duplicate descriptions | Pages compete | Mostly the brand pairs (handled by canonicals); write unique ones for the rest |
| Structured data: business `geo` is Toronto city centre (43.6532, -79.3832), address has no street, `priceRange` "$" | Weak local signals; mismatch with a real Google Business Profile | Use the real business location or mark it a service-area business; match the Google Business Profile exactly |
| Accessibility 87: low-contrast text, links without names, skipped heading levels | Usability, minor ranking signal | Fix contrast on the light-blue text and add labels to icon-only links |
| No text compression or cache headers (on the test server) | Large transfers | Configure on the real host: gzip/brotli, long cache for `/assets/` |

## Next steps

1. Decide what this site is for: whose business it represents, which domain.
2. Rebrand and rewrite (or regenerate it with the site builder skill).
3. Decide on the page cut (services, brands, cities) and add 301 redirects for removed URLs.
4. Run `tools/seo_finalize.py --site-url ...` and re-run the audit:
   `python3 .claude/skills/local-service-site-builder/scripts/seo_audit.py . --site-url https://your-domain`
5. After launch: Search Console, sitemap submission, Google Business Profile with matching name, address and phone.
