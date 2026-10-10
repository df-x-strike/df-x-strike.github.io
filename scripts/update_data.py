"""Met à jour data/projects.json (GitHub) et data/videos.json (YouTube)."""
import json, os, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

USER = "df-x-strike"
EXCLUDE = {USER, f"{USER}.github.io"}                      # dépôts à ne pas afficher
CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "").strip()   # ex. UCxxxxxxxxxxxxxxxxxxxxxx

def get(url, headers=None):
    h = {"User-Agent": "portfolio-updater"}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read()

def save(path, items):
    try:
        old = json.load(open(path, encoding="utf-8")).get("items")
    except Exception:
        old = None
    if old == items:
        return  # rien de nouveau : pas de commit inutile
    data = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": items}
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def projects():
    hdr = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        hdr["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed", hdr))
    items = [{"name": r["name"], "url": r["html_url"], "description": r["description"],
              "language": r["language"], "topics": r.get("topics", []), "pushed_at": r["pushed_at"]}
             for r in repos if not r["fork"] and not r["archived"] and r["name"] not in EXCLUDE]
    return sorted(items, key=lambda i: i["pushed_at"], reverse=True)

def videos():
    if not CHANNEL_ID:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom", "y": "http://www.youtube.com/xml/schemas/2015"}
    root = ET.fromstring(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"))
    return [{"id": e.find("y:videoId", ns).text, "title": e.find("a:title", ns).text,
             "published": e.find("a:published", ns).text} for e in root.findall("a:entry", ns)][:6]

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    for name, fn in (("projects", projects), ("videos", videos)):
        try:
            save(f"data/{name}.json", fn())
        except Exception as ex:   # une erreur n'écrase jamais les anciennes données
            print(f"{name}: erreur ignorée -> {ex}")
