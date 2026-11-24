#!/usr/bin/env python3
"""Hämtar RSS-flöden från källorna i sources.json, grupperar artiklar som
handlar om samma händelse och skriver news.json som sidan läser.

Kör:  python scripts/fetch_news.py --sources sources.json --out site/news.json
Test utan nät:  python scripts/fetch_news.py --items artiklar.tsv --out site/news.json
  (TSV-kolumner: [valfri], källa-id, datum, url, rubrik)
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

STOP = set("""
och i att det som en på är av för med till den har de inte om ett han men var jag sig från vi så kan
man när år säger hon under också efter eller nu sin där vid mot ska skulle kommer ut får finns vara
hade alla andra mycket än här då sedan över bara in blir upp även vad få två vill ha många hur mer går
därför gör utan nya ny nytt varför ännu mellan igen tre första enligt inför just både dock hela helt
redan mest själv deras dess hans hennes vår våra er ni oss dem dom denna detta dessa vilka vilken
vilket någon något några ingen inget inga varje samma sådan mitt ditt min din sina sitt uppgifter
live analys ledare krönika debatt replik slutreplik video bilder se här kl efter så nu dag dagen
""".split())
PARTIES = {"s", "v", "c", "l", "m", "kd", "sd", "mp"}
WORD = re.compile(r"[a-zåäöéü0-9]+")


def tokens(text):
    out = []
    for w in WORD.findall(text.lower()):
        if w in PARTIES:
            out.append("parti_" + w)
        elif len(w) >= 3 and w not in STOP and not w.isdigit():
            out.append(w[:6])  # grov stam: fångar böjningar och sammansättningar
    return out


def parse_date(raw):
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def fetch_feeds(cfg):
    import feedparser  # pip install feedparser

    items = []
    for src in cfg["sources"]:
        if src.get("enabled") is False:
            continue
        feed = feedparser.parse(src["feed"], agent="HelaBilden/1.0 (+RSS-aggregator)")
        if feed.bozo and not feed.entries:
            print(f"! {src['id']}: kunde inte läsa flödet ({feed.bozo_exception})", file=sys.stderr)
            continue
        n = 0
        for e in feed.entries:
            date = None
            for key in ("published_parsed", "updated_parsed"):
                if e.get(key):
                    date = datetime(*e[key][:6], tzinfo=timezone.utc)
                    break
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            if not title or not link.startswith("https://") or not date:
                continue
            desc = re.sub(r"<[^>]+>", " ", e.get("summary") or "")
            items.append({"s": src["id"], "t": title, "u": link, "d": date, "x": desc[:400]})
            n += 1
        print(f"  {src['id']}: {n} artiklar", file=sys.stderr)
    return items


def read_tsv(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            _, s, d, u, t = parts[:5]
            date = parse_date(d)
            if date:
                items.append({"s": s, "t": t, "u": u, "d": date, "x": ""})
    return items


def cluster(items, threshold=0.2, window_h=48):
    """Enkel inkrementell gruppering: TF-IDF-vektorer på rubrik (+ ingress),
    varje artikel läggs i den grupp vars centroid den liknar mest."""
    docs = [Counter(tokens(it["t"] + " " + it["t"] + " " + it.get("x", ""))) for it in items]
    df = Counter()
    for d in docs:
        df.update(d.keys())
    n = len(docs)
    idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}

    def vec(d):
        v = {w: tf * idf[w] for w, tf in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    vecs = [vec(d) for d in docs]
    order = sorted(range(n), key=lambda i: items[i]["d"])
    groups = []  # {"members": [i], "centroid": {}, "last": dt}
    for i in order:
        v = vecs[i]
        best, best_sim = None, 0.0
        for g in groups:
            if items[i]["d"] - g["last"] > timedelta(hours=window_h):
                continue
            sim = sum(x * g["centroid"].get(w, 0.0) for w, x in v.items())
            if sim > best_sim:
                best, best_sim = g, sim
        if best and best_sim >= threshold:
            best["members"].append(i)
            k = len(best["members"])
            c = best["centroid"]
            for w in set(c) | set(v):
                c[w] = (c.get(w, 0.0) * (k - 1) + v.get(w, 0.0)) / k
            best["last"] = max(best["last"], items[i]["d"])
        else:
            groups.append({"members": [i], "centroid": dict(v), "last": items[i]["d"]})
    return groups, vecs


def build(items, cfg, snapshot=False, note=""):
    lean = {s["id"]: s["lean"] for s in cfg["sources"]}
    groups, vecs = cluster(items, window_h=cfg.get("window_hours", 48))
    stories = []
    for g in groups:
        mem = g["members"]
        # representativ rubrik: närmast centroiden, mittenkällor vinner vid lika
        rep = max(mem, key=lambda i: (round(sum(x * g["centroid"].get(w, 0) for w, x in vecs[i].items()), 3),
                                      -abs(lean.get(items[i]["s"], 0))))
        arts = sorted(mem, key=lambda i: items[i]["d"], reverse=True)
        sid = hashlib.sha1(items[rep]["u"].encode()).hexdigest()[:10]
        stories.append({
            "id": sid,
            "title": items[rep]["t"],
            "summary": "",
            "updated": max(items[i]["d"] for i in mem).isoformat(),
            "articles": [{"s": items[i]["s"], "t": items[i]["t"], "u": items[i]["u"],
                          "d": items[i]["d"].isoformat()} for i in arts],
        })
    used = {it["s"] for it in items}
    sources = [dict(s, inSnapshot=s["id"] in used) for s in cfg["sources"]]
    for s in sources:
        s.pop("feed", None)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot": snapshot,
        "note": note,
        "sources": sources,
        "stories": stories,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="sources.json")
    ap.add_argument("--out", default="site/news.json")
    ap.add_argument("--items", help="läs artiklar från TSV i stället för att hämta flöden")
    args = ap.parse_args()

    with open(args.sources, encoding="utf-8") as f:
        cfg = json.load(f)

    items = read_tsv(args.items) if args.items else fetch_feeds(cfg)
    pats = [re.compile(p) for p in cfg.get("exclude_url_patterns", [])]
    items = [it for it in items if not any(p.search(it["u"]) for p in pats)]
    if not args.items:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=cfg.get("window_hours", 48))
        items = [it for it in items if it["d"] >= cutoff]
    regional = {s["id"] for s in cfg["sources"] if s.get("region")}
    items.sort(key=lambda it: 0 if it["s"] in regional else 1)  # lokal källa vinner vid dubbletter
    seen, unique = set(), []
    for it in items:  # samma länk i flera flöden räknas en gång
        if it["u"] not in seen:
            seen.add(it["u"])
            unique.append(it)

    data = build(unique, cfg)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    multi = sum(1 for s in data["stories"] if len({a["s"] for a in s["articles"]}) > 1)
    print(f"Klart: {len(unique)} artiklar, {len(data['stories'])} händelser ({multi} med flera källor) -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
