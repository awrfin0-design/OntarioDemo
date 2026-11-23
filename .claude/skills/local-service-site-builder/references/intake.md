# Intake questions

Ask these in one message. Mark which are required. Use the answers exactly; never fill gaps with invented facts.

| # | Question | Required | Used for |
|---|---|---|---|
| 1 | Business name (as on signage / Google Business Profile) and legal name | yes | Header, schema `name`, footer |
| 2 | Industry and the 3–8 services you most want to sell | yes | Service pages, nav, schema type, calculator |
| 3 | Home base and the communities you serve (and how far you'll drive) | yes | Areas, `areaServed`, pricing regions |
| 4 | Domain (or the one you plan to buy) | yes | Canonicals, sitemap, Open Graph |
| 5 | Phone and email shown to customers | yes | Click-to-call, schema, forms |
| 6 | Street address, or "service-area business, no public address" | yes | Schema `address`, footer. Only show a street address customers can visit or that is on the Google Business Profile |
| 7 | Opening hours, and whether there's a 24/7 emergency line | yes | Schema `openingHoursSpecification`, header, footer |
| 8 | Year founded, team size, licences, insurance, certifications, warranties | yes (whatever is true) | Trust strip, About, Why-us. Omit anything that isn't true |
| 9 | What makes you different from the other companies in town? | yes | Hero, Why-us. Push for specifics (equipment, process, guarantees, response time) |
| 10 | Typical jobs and the problems customers call about | yes | Service page content, FAQ |
| 11 | Price ranges per service and job type (repair / maintenance / install), and extra charges for same-day or after-hours | for calculator | Pricing calculator, price tables |
| 12 | Does price differ by area? Which areas cost more or less, by roughly how much? | for calculator | Pricing regions |
| 13 | 3–10 real customer reviews with first name + initial, area, and source (Google, HomeStars…) | no | Reviews section. Leave out if none |
| 14 | Photos: team, vehicles, before/after, finished jobs | strongly recommended | Hero, services, about, og image |
| 15 | Logo (SVG or large PNG) and brand colours, if any | no | Overrides the generated palette |
| 16 | Form destination: Formspree / Netlify Forms / own endpoint / email | no | `form.endpoint`. Without it the form tells visitors to call |
| 17 | Social and directory profiles (Google Business Profile, Facebook, HomeStars, BBB…) | no | `sameAs` in schema, footer |

## Local research (do this yourself)

For each community that might get its own page, collect at least three facts that change how the job is done
or what the customer should know. Good examples:

- Housing stock: era, construction type, typical pipe/wiring/roofing materials
- Water: municipal vs well, hardness, iron
- Climate: freeze-thaw, coastal wind/salt, humidity, heat waves, flood zones
- Rules: permits, inspections, rebates or utility programs that really exist (link the source)
- Logistics: drive time from the shop, which days a crew is in the area

Not good: population figures, "beautiful parks", lists of landmarks, or anything that would read the same for
any trade.

If you can't find three real facts, the community goes in the list on the Service Areas page only.
