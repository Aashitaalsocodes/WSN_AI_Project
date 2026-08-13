"""
Fixes App.jsx so it uses the local dev proxy path in development,
but the absolute Render URL in the production build (Netlify).
Run from frontend/dashboard:
    python patch_fix_prod_api_url.py
"""
PATH = "src/App.jsx"
OLD = "    fetch('/api/dashboard-formatted')"
NEW = (
    "    const API_BASE = import.meta.env.DEV ? '' : 'https://wsn-ai-project.onrender.com'\n"
    "    fetch(`${API_BASE}/api/dashboard-formatted`)"
)
with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()
if OLD not in src:
    raise SystemExit("ABORT: expected fetch line not found — file may have changed. No edits made.")
src = src.replace(OLD, NEW, 1)
with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("Patched App.jsx: uses '' (dev proxy) in dev, absolute Render URL in production build.")