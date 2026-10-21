#!/usr/bin/env python3
"""Enrich non-Turkey countries with verified streams; sort alphabetically."""
from __future__ import annotations

import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "legal_world_by_country.m3u"
RESEARCH = Path(os.environ["TEMP"]) / "iptv-research"
FREETV = RESEARCH / "freetv.m3u8"

# bilingual group -> (iso code, Free-TV English group names)
COUNTRIES = {
    "Argentina / Arjantin": ("ar", ["Argentina"]),
    "Australia / Avustralya": ("au", ["Australia"]),
    "Brazil / Brezilya": ("br", ["Brazil"]),
    "Canada / Kanada": ("ca", ["Canada"]),
    "China / Çin": ("cn", ["China"]),
    "Denmark / Danimarka": ("dk", ["Denmark"]),
    "France / Fransa": ("fr", ["France"]),
    "Germany / Almanya": ("de", ["Germany"]),
    "India / Hindistan": ("in", ["India"]),
    "Indonesia / Endonezya": ("id", ["Indonesia"]),
    "Italy / İtalya": ("it", ["Italy"]),
    "Japan / Japonya": ("jp", ["Japan", "日本 / Japan"]),
    "Mexico / Meksika": ("mx", ["Mexico"]),
    "Netherlands / Hollanda": ("nl", ["Netherlands"]),
    "Norway / Norveç": ("no", ["Norway"]),
    "Poland / Polonya": ("pl", ["Poland"]),
    "Portugal / Portekiz": ("pt", ["Portugal"]),
    "Qatar / Katar": ("qa", ["Qatar"]),
    "Romania / Romanya": ("ro", ["Romania"]),
    "Saudi Arabia / Suudi Arabistan": ("sa", ["Saudi Arabia"]),
    "Singapore / Singapur": ("sg", ["Singapore"]),
    "South Korea / Güney Kore": ("kr", ["Korea"]),
    "Spain / İspanya": ("es", ["Spain"]),
    "Sweden / İsveç": ("se", ["Sweden"]),
    "Turkey / Türkiye": ("tr", ["Turkey"]),
    "UAE / BAE": ("ae", ["United Arab Emirates"]),
    "USA / ABD": ("us", ["USA"]),
    "United Kingdom / İngiltere": ("uk", ["UK"]),
}

TARGET_MIN = 20  # aim at least this many per country (Turkey already rich)
TARGET_MAX = 50
MARKERS = re.compile(r"[ⓈⒼⓎⒹ]")
IP_HOST = re.compile(r"://\d+\.\d+\.\d+\.\d+")
BAD_HOST = (
    "youtube",
    "youtu.be",
    "dailymotion",
    "jmp2.uk",
    "mangeinde4",
    "androstream",
    "siteyaptim",
    "playhdnew",
    "onrender.com",
    "mugla.tvizle",
    "iptvmaster",
)


def clean_name(name: str) -> str:
    name = MARKERS.sub("", name)
    name = re.sub(r"\s*\[[^\]]*\]\s*", " ", name)
    # drop trailing (720p) etc
    name = re.sub(r"\s*\(\d+p\)\s*$", "", name, flags=re.I)
    name = re.sub(r"\s*\([^)]*Not 24/7[^)]*\)\s*", " ", name, flags=re.I)
    name = re.sub(r"\s*\([^)]*Geo-blocked[^)]*\)\s*", " ", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def parse_m3u(text: str) -> list[dict]:
    items = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF:"):
            info = lines[i]
            url = lines[i + 1].strip() if i + 1 < len(lines) and not lines[i + 1].startswith("#") else ""
            name_m = re.search(r",(.+)$", info)
            raw = name_m.group(1).strip() if name_m else ""
            logo_m = re.search(r'tvg-logo="([^"]*)"', info)
            id_m = re.search(r'tvg-id="([^"]*)"', info)
            group_m = re.search(r'group-title="([^"]*)"', info)
            items.append(
                {
                    "name": clean_name(raw),
                    "raw": raw,
                    "logo": logo_m.group(1) if logo_m else "",
                    "id": id_m.group(1) if id_m else "",
                    "group": group_m.group(1) if group_m else "",
                    "url": url,
                }
            )
            i += 2
        else:
            i += 1
    return items


def is_clean_url(url: str) -> bool:
    if not url or not url.startswith("https://"):
        return False
    if ".m3u8" not in url.lower():
        return False
    low = url.lower()
    if any(b in low for b in BAD_HOST):
        return False
    if IP_HOST.search(url):
        return False
    return True


def test_ok(url: str, timeout: int = 10) -> bool:
    for extra in ([], ["-k"]):
        try:
            r = subprocess.run(
                [
                    "curl.exe",
                    *extra,
                    "-sL",
                    "--max-time",
                    str(timeout),
                    "-A",
                    "Mozilla/5.0",
                    "-o",
                    "-",
                    "-w",
                    "\n__CODE__%{http_code}",
                    url,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            continue
        out = r.stdout or ""
        m = re.search(r"__CODE__(\d+)", out)
        code = int(m.group(1)) if m else 0
        body = re.sub(r"__CODE__\d+\s*$", "", out)
        if 200 <= code < 400 and ("#EXTM3U" in body or "#EXT-X-" in body):
            return True
    return False


def priority(name: str) -> int:
    """Lower = better (news / public / national first)."""
    n = name.casefold()
    keys = (
        "news",
        "world",
        "public",
        "rai ",
        "rtp",
        "bbc",
        "ard",
        "zdf",
        "france",
        "dw ",
        "cnn",
        "abc",
        "cbs",
        "nbc",
        "pbs",
        "nhk",
        "cgtn",
        "al jazeera",
        "bloomberg",
        "nasa",
        "parliament",
        "senat",
        "congress",
        "kanal",
        "tv ",
        "radio",
    )
    for i, k in enumerate(keys):
        if k in n:
            return i
    return 100


def load_sources(iso: str, ft_groups: list[str]) -> list[dict]:
    out: list[dict] = []
    country_file = RESEARCH / f"{iso}.m3u"
    if country_file.exists():
        out.extend(parse_m3u(country_file.read_text(encoding="utf-8")))
    if FREETV.exists():
        ft = parse_m3u(FREETV.read_text(encoding="utf-8"))
        for it in ft:
            if it["group"] in ft_groups:
                out.append(it)
    # dedupe by url
    seen = set()
    uniq = []
    for it in out:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    return uniq


def main() -> int:
    existing = parse_m3u(OUT.read_text(encoding="utf-8"))
    # group -> list of channels
    by_group: dict[str, list[dict]] = {g: [] for g in COUNTRIES}
    seen_names: set[str] = set()
    seen_urls: set[str] = set()

    print("Keeping existing (re-verify)...")
    # Keep existing without full retest to save time — user asked working links for NEW ones;
    # still drop obvious bad. Quick retest only for non-Turkey thin? Retest all existing in parallel.
    def keep_one(it: dict) -> dict | None:
        if not it["name"] or not it["url"]:
            return None
        if it["name"].casefold() in seen_names:
            return None
        if not test_ok(it["url"]):
            print(f"  DROP dead: {it['group']} / {it['name']}")
            return None
        return it

    # Parallel re-verify existing
    kept: list[dict] = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(test_ok, it["url"]): it for it in existing}
        for fut in as_completed(futs):
            it = futs[fut]
            ok = fut.result()
            if not ok:
                print(f"  DROP dead: {it['group']} / {it['name']}")
                continue
            key = it["name"].casefold()
            if key in seen_names or it["url"] in seen_urls:
                continue
            # normalize group if old
            g = it["group"]
            if g not in by_group:
                # try match turkish-only leftover
                for bg in by_group:
                    if g in bg or bg.endswith(g):
                        g = bg
                        break
            if g not in by_group:
                print(f"  SKIP unknown group: {it['group']} / {it['name']}")
                continue
            ch = {
                "name": it["name"],
                "logo": it["logo"],
                "id": it["id"] or it["name"],
                "group": g,
                "url": it["url"],
            }
            by_group[g].append(ch)
            seen_names.add(key)
            seen_urls.add(it["url"])
            kept.append(ch)

    print(f"Kept {len(kept)} existing channels")

    # Enrich each country except skip if already at TARGET_MAX
    for group, (iso, ft_groups) in sorted(COUNTRIES.items()):
        current = len(by_group[group])
        if current >= TARGET_MAX:
            print(f"\n{group}: already {current}, skip enrich")
            continue
        need = TARGET_MAX - current if group.startswith("Turkey") else max(TARGET_MIN - current, 0)
        # For non-Turkey, try to reach at least TARGET_MIN, preferably more up to TARGET_MAX
        if not group.startswith("Turkey"):
            need = TARGET_MAX - current
        if need <= 0:
            continue

        print(f"\n{group}: have {current}, seeking +{need}...")
        sources = load_sources(iso, ft_groups)
        # filter candidates
        cands = []
        for it in sources:
            name = it["name"]
            if not name or not it["logo"] or not is_clean_url(it["url"]):
                continue
            if name.casefold() in seen_names or it["url"] in seen_urls:
                continue
            cands.append(it)
        cands.sort(key=lambda x: (priority(x["name"]), x["name"].casefold()))

        # Cap attempts to avoid endless testing
        max_attempts = min(len(cands), need * 4 + 30)
        to_test = cands[:max_attempts]
        print(f"  candidates={len(cands)} testing={len(to_test)}")

        added = 0
        with ThreadPoolExecutor(max_workers=20) as ex:
            futs = {ex.submit(test_ok, it["url"]): it for it in to_test}
            # Process in priority order as they complete — still need limit
            results_ok: list[dict] = []
            for fut in as_completed(futs):
                it = futs[fut]
                if fut.result():
                    results_ok.append(it)

        # Sort successful by priority then name, take until need filled
        results_ok.sort(key=lambda x: (priority(x["name"]), x["name"].casefold()))
        for it in results_ok:
            if added >= need:
                break
            name = it["name"]
            if name.casefold() in seen_names or it["url"] in seen_urls:
                continue
            if not it["logo"]:
                continue
            ch = {
                "name": name,
                "logo": it["logo"],
                "id": it["id"] or name,
                "group": group,
                "url": it["url"],
            }
            by_group[group].append(ch)
            seen_names.add(name.casefold())
            seen_urls.add(it["url"])
            added += 1
            print(f"  + {name}")

        print(f"  -> {len(by_group[group])} total (+{added})")

    # Build output: groups A-Z by English name, channels A-Z within
    lines = [
        "#EXTM3U",
        "# Owl IP Player — yasal / kamuya açık canlı yayınlar (ülke gruplu)",
        "# Kaynaklar: Free-TV/IPTV + iptv-org + yayıncı HLS",
        "# Not: Bazı akışlar coğrafi kısıtlı veya zamanla değişebilir. Ticari şifreli kanallar yoktur.",
        "# Güncelleme: 2026-10-22 (ülkeler zenginleştirildi; alfabetik; doğrulanmış)",
        "",
    ]

    total = 0
    for group in sorted(by_group.keys(), key=lambda g: g.casefold()):
        channels = by_group[group]
        if not channels:
            continue
        channels.sort(key=lambda c: c["name"].casefold())
        lines.append(f"# ── {group} ──────────────────────────────────────────────────────────")
        for ch in channels:
            lines.append(
                f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" '
                f'tvg-logo="{ch["logo"]}" group-title="{group}",{ch["name"]}'
            )
            lines.append(ch["url"])
            total += 1

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n=== DONE ===")
    print(f"Total channels: {total}")
    for group in sorted(by_group.keys(), key=lambda g: g.casefold()):
        n = len(by_group[group])
        if n:
            print(f"  {group}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
