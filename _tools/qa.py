"""
Static QA over the generated site. Run after Build-Site.ps1.

Checks, in order of how much they'd hurt if wrong:
  1. Internal links resolve to a file that exists
  2. Every <script type="application/ld+json"> block is valid JSON
  3. Required <head> tags present (title, description, canonical, og:image, robots)
  4. Canonical matches the page's own URL (no copy-paste carryover)
  5. No unreplaced {{TOKEN}} and no <mark class="todo"> placeholders
  6. Only CSS classes that exist in the stylesheet are used
  7. Every <img> has alt, every anchor has text, one <h1> per page
"""
import io, json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://datainsightsnorthwest.co.uk"

def read(p):
    return io.open(p, encoding="utf-8").read()

# ---------------------------------------------------------------- collect
pages = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if not d.startswith((".", "_")) and d not in ("paperwork",)]
    for fn in filenames:
        if not fn.endswith(".html"):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        if rel.startswith(("_", ".")) or rel.startswith("google"):
            continue
        pages.append(rel)
pages.sort()

css = read(os.path.join(ROOT, "assets", "styles.css"))
css_classes = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))

problems = defaultdict(list)

def fail(page, msg):
    problems[page].append(msg)

# ---------------------------------------------------------------- per page
for rel in pages:
    html = read(os.path.join(ROOT, rel))

    # -- 5. tokens / placeholders
    for tok in set(re.findall(r"\{\{([A-Z_]+)\}\}", html)):
        fail(rel, f"unreplaced token {{{{{tok}}}}}")
    todos = re.findall(r'<mark class="todo">(.*?)</mark>', html, re.S)
    for t in todos:
        fail(rel, f"TODO placeholder: {' '.join(t.split())[:90]}")

    # -- 3. head tags
    if not re.search(r"<title>.+?</title>", html, re.S):
        fail(rel, "missing <title>")
    if not re.search(r'<meta name="description" content=".+?">', html, re.S):
        fail(rel, "missing meta description")
    if not re.search(r'<meta name="robots"', html):
        fail(rel, "missing meta robots")
    for prop in ("og:title", "og:description", "og:image", "og:url", "twitter:card"):
        if prop not in html:
            fail(rel, f"missing {prop}")

    # -- 4. canonical correctness
    m = re.search(r'<link rel="canonical" href="([^"]+)">', html)
    if not m:
        fail(rel, "missing canonical")
    else:
        want = f"{DOMAIN}/" if rel == "index.html" else f"{DOMAIN}/{rel}"
        if m.group(1) != want:
            fail(rel, f"canonical is {m.group(1)}, expected {want}")

    # -- 2. JSON-LD validity
    for i, block in enumerate(re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S)):
        try:
            json.loads(block)
        except Exception as e:
            fail(rel, f"JSON-LD block {i + 1} invalid: {e}")

    # -- 7. accessibility / structure
    h1s = re.findall(r"<h1[ >]", html)
    if len(h1s) != 1:
        fail(rel, f"{len(h1s)} <h1> tags (want exactly 1)")
    for img in re.findall(r"<img\b[^>]*>", html):
        if "alt=" not in img:
            fail(rel, f"<img> without alt: {img[:70]}")
    for a in re.findall(r"<a\b[^>]*>\s*</a>", html):
        fail(rel, f"empty link: {a[:70]}")

    # -- 6. class names that do not exist in the stylesheet
    used = set()
    for attr in re.findall(r'class="([^"]+)"', html):
        used.update(attr.split())
    for cls in sorted(used - css_classes):
        # SVG presentation classes and utility one-offs live in the stylesheet;
        # anything else is a typo or an invented class.
        fail(rel, f"class '{cls}' not defined in styles.css")

    # -- 1. internal links
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            continue
        path, _, frag = href.partition("#")
        if not path:
            continue
        if not path.startswith("/"):
            fail(rel, f"link not root-relative: {href}")
            continue
        target = path.lstrip("/")
        if target == "":
            target = "index.html"
        if not os.path.exists(os.path.join(ROOT, target.replace("/", os.sep))):
            fail(rel, f"broken link -> {href}")
        elif frag and target.endswith(".html"):
            th = read(os.path.join(ROOT, target.replace("/", os.sep)))
            if f'id="{frag}"' not in th:
                fail(rel, f"missing anchor #{frag} in {target}")

# ---------------------------------------------------------------- sitemap
sm = read(os.path.join(ROOT, "sitemap.xml"))
listed = set(re.findall(r"<loc>(.*?)</loc>", sm))
for rel in pages:
    html = read(os.path.join(ROOT, rel))
    noindexed = 'content="noindex' in html
    url = f"{DOMAIN}/" if rel == "index.html" else f"{DOMAIN}/{rel}"
    if noindexed and url in listed:
        fail(rel, "noindex page is listed in sitemap.xml")
    if not noindexed and url not in listed:
        fail(rel, "indexable page missing from sitemap.xml")

# ---------------------------------------------------------------- report
print(f"Checked {len(pages)} pages\n")
if not problems:
    print("ALL CHECKS PASS")
    sys.exit(0)

total = sum(len(v) for v in problems.values())
for page in sorted(problems):
    print(f"  {page}")
    for msg in problems[page]:
        print(f"      - {msg}")
    print()
print(f"{total} problem(s) across {len(problems)} page(s)")
sys.exit(1)
