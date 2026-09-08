# datainsightsnorthwest.co.uk

The website for **Data Insights North West** — Power BI and Excel reporting, report automation
and data analysis for businesses across Merseyside, the North West and UK-wide.

Live at <https://datainsightsnorthwest.co.uk> · hosted on GitHub Pages · domain and DNS on
Cloudflare.

## Editing the site

The HTML files in the repo root are **generated**. Edit `_src/` and rebuild:

```powershell
.\_tools\Build-Site.ps1      # assemble _src/ into the repo root
py .\_tools\qa.py            # link, schema, meta and accessibility checks
py -m http.server 8731       # preview at http://127.0.0.1:8731/
```

Then commit and push — GitHub Pages redeploys automatically, usually within a minute.

`_src/` and `_tools/` start with an underscore so Jekyll never publishes them. Do not add a
`.nojekyll` file.

## Do not delete

- `CNAME` — the custom domain
- `googlea4b8db69c89cd24d.html` — Google Search Console verification

## More

See `CLAUDE.md` for the full conventions: brand tokens, the validated chart palette, content
rules, and what must never be committed to this public repo.
