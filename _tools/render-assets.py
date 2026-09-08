"""
Rasterise the brand assets that have to be PNG.

Two of them cannot be SVG:
  - assets/social-card.png  — LinkedIn, WhatsApp, Slack and X do not render SVG
    for og:image, so the share card must be a bitmap.
  - assets/app-icon-180.png — iOS apple-touch-icon ignores SVG.
  - assets/logo-lockup.png  — for directories, invoices and email signatures,
    where the Space Grotesk / Inter webfonts will not be installed.

Rendered through headless Chrome so the Google-hosted webfonts are actually
applied, then trimmed/verified with Pillow.

Usage:  py _tools/render-assets.py
"""
import os, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

FONTS = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?'
         'family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700'
         '&display=block" rel="stylesheet">')

MARK = """
<svg viewBox="0 0 32 32" width="{size}" height="{size}">
  <rect width="32" height="32" rx="7.5" fill="{tile}"/>
  <rect x="6" y="26.6" width="20" height="1.2" rx=".6" fill="#fff" opacity=".18"/>
  <rect x="6" y="18" width="5" height="8" rx="1.5" fill="#2FB574"/>
  <rect x="13.5" y="12.5" width="5" height="13.5" rx="1.5" fill="#2FB574"/>
  <rect x="21" y="7" width="5" height="19" rx="1.5" fill="#F2C24B"/>
</svg>
"""

# --- the social share card ---------------------------------------------------
SOCIAL = """<!doctype html><meta charset="utf-8">""" + FONTS + """
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1200px;height:630px;overflow:hidden}
  body{
    background:#0E1A24; color:#fff; font-family:Inter,sans-serif;
    padding:74px 78px; display:flex; flex-direction:column; position:relative;
  }
  /* Recessive chart motif, bottom-right — decoration that is at least on-brand */
  .motif{position:absolute;right:-30px;bottom:-10px;width:540px;opacity:.17}
  .top{display:flex;align-items:center;gap:18px}
  .wm{display:flex;flex-direction:column;line-height:1}
  .wm .t1{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:34px;letter-spacing:-.03em}
  .wm .t2{display:flex;align-items:center;gap:11px;margin-top:9px}
  .wm .t2 i{width:26px;height:2px;background:#C9A24A;display:block;border-radius:1px}
  .wm .t2 span{font-weight:600;font-size:15px;letter-spacing:.26em;color:#2FB574}
  h1{
    font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:60px;
    letter-spacing:-.032em;line-height:1.08;margin-top:auto;max-width:20ch;
    position:relative;z-index:1;
  }
  .sub{font-size:22px;color:#A9BAC1;margin-top:22px;position:relative;z-index:1}
  .foot{
    margin-top:auto;display:flex;gap:26px;align-items:center;
    font-size:17px;color:#7C9099;position:relative;z-index:1;
  }
  .foot b{color:#fff;font-weight:600}
</style>
<svg class="motif" viewBox="0 0 620 300" fill="none">
  <g fill="#2FB574">
    <rect x="20"  y="200" width="44" height="100" rx="6"/>
    <rect x="88"  y="170" width="44" height="130" rx="6"/>
    <rect x="156" y="182" width="44" height="118" rx="6"/>
    <rect x="224" y="140" width="44" height="160" rx="6"/>
    <rect x="292" y="150" width="44" height="150" rx="6"/>
    <rect x="360" y="104" width="44" height="196" rx="6"/>
    <rect x="428" y="118" width="44" height="182" rx="6"/>
  </g>
  <rect x="496" y="60" width="44" height="240" rx="6" fill="#F2C24B"/>
</svg>
<div class="top">
  """ + MARK.format(size=68, tile="#16232E") + """
  <div class="wm">
    <div class="t1">Data Insights</div>
    <div class="t2"><i></i><span>NORTH WEST</span></div>
  </div>
</div>
<h1>The reports just arrive, correct, every time.</h1>
<p class="sub">Power BI &amp; Excel reporting &middot; automation &middot; data analysis</p>
<div class="foot"><b>datainsightsnorthwest.co.uk</b><span>Merseyside &middot; North West &middot; UK-wide</span></div>
"""

# --- the horizontal lockup, transparent background ---------------------------
LOCKUP = """<!doctype html><meta charset="utf-8">""" + FONTS + """
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:900px;height:200px;background:transparent}
  body{display:flex;align-items:center;gap:26px;padding:0 24px;font-family:Inter,sans-serif}
  .wm{display:flex;flex-direction:column;line-height:1}
  .wm .t1{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:62px;letter-spacing:-.032em;color:#0E1A24}
  .wm .t2{display:flex;align-items:center;gap:16px;margin-top:14px}
  .wm .t2 i{width:44px;height:3px;background:#C9A24A;display:block;border-radius:2px}
  .wm .t2 span{font-weight:600;font-size:26px;letter-spacing:.26em;color:#0F7A52}
</style>
""" + MARK.format(size=118, tile="#0E1A24") + """
<div class="wm">
  <div class="t1">Data Insights</div>
  <div class="t2"><i></i><span>NORTH WEST</span></div>
</div>
"""

ICON = """<!doctype html><meta charset="utf-8">
<style>*{margin:0;padding:0}html,body{width:180px;height:180px;overflow:hidden}</style>
""" + MARK.format(size=180, tile="#0E1A24")


JOBS = [
    ("social-card.png",   SOCIAL,  1200, 630, False),
    ("logo-lockup.png",   LOCKUP,   900, 200, True),
    ("app-icon-180.png",  ICON,     180, 180, False),
]


def find_browser():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("No Chrome or Edge found for rendering.")


def main():
    browser = find_browser()
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="dinw-render-")
    try:
        for name, html, w, h, transparent in JOBS:
            src = os.path.join(tmp, name + ".html")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(html)
            dest = os.path.join(OUT, name)
            cmd = [
                browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--virtual-time-budget=8000",
                f"--window-size={w},{h}",
                f"--screenshot={dest}",
            ]
            if transparent:
                cmd.append("--default-background-color=00000000")
            cmd.append(src)
            subprocess.run(cmd, capture_output=True, timeout=120)
            if not os.path.exists(dest):
                sys.exit(f"FAILED to render {name}")
            from PIL import Image
            with Image.open(dest) as im:
                print(f"  {name:22} {im.size[0]}x{im.size[1]}  "
                      f"{os.path.getsize(dest) // 1024} KB  mode={im.mode}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nRendered into assets/. Re-run Build-Site.ps1 is NOT needed "
          "(these are written straight to assets/).")


if __name__ == "__main__":
    main()
