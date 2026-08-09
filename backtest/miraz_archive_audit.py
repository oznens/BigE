#!/usr/bin/env python3
"""@tradermiraz arşivinden terminalMiraz davranışları için kanıt özeti üretir.

Bu script strateji kuralı icat etmez. tweetler.json + tweet_gorsel.json içinden
kritik ifadeleri sayar, yüksek-etkileşimli örnekleri ve bağlı chart dosyalarını
raporlar. Amaç canlı klon kurallarını kanıta bağlamaktır.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TW = ROOT / "tweetler" / "tweetler.json"
MAP = ROOT / "tweetler" / "tweet_gorsel.json"
OUT_MD = ROOT / "tweetler" / "TERMINALMIRAZ_EVIDENCE.md"
OUT_JSON = ROOT / "tweetler" / "terminalmiraz_evidence.json"

GROUPS = {
    "terminal": [r"terminal\s*miraz", r"terminal"],
    "trigger": [r"trend\s*k[ıi]r[ıi]l", r"yeşil\s*daire", r"teyit", r"onay"],
    "volume_close": [r"hacimli\s*kapan", r"hacim.*kapan", r"kapan.*hacim"],
    "close_invalidation": [r"alt[ıi]nda\s+kapan", r"[üu]st[üu]nde\s+kapan", r"kapan[ıi]ş.*iptal", r"ge[çc]ersiz"],
    "partial_be": [r"k[âa]r\s*al", r"kar\s*al", r"giri[şs]e\s*stop", r"stop.*giri[şs]", r"breakeven", r"break\s*even", r"risksiz"],
    "rr": [r"\b1\s*[rR]\b", r"\b2\s*[rR]\b", r"1\s*[:/]\s*2", r"risk\s*/?\s*reward", r"risk.*reward"],
    "risk_modes": [r"a[şs][ıi]r[ıi]\s*g[üu]venli", r"dengeli", r"tamamen\s*riskli"],
    "harmonic": [r"harmonik", r"gartley", r"butterfly", r"kelebek", r"bat\b", r"crab", r"yenge[çc]", r"cypher", r"shark", r"prz"],
    "retest": [r"re[- ]?test", r"geri\s*test", r"k[ıi]r[ıi]l.*test"],
}

PCT_RE = re.compile(r"(?:%\s*\d{1,3}|\b\d{1,3}\s*%)")
RR_RE = re.compile(r"(?:\b\d+(?:[.,]\d+)?\s*[rR]\b|\b\d+(?:[.,]\d+)?\s*[:/]\s*\d+(?:[.,]\d+)?\b)")


def norm(s: str) -> str:
    return (s or "").lower().replace("ı", "i").replace("İ", "i")


def score(t: dict) -> int:
    return int(t.get("likeCount") or 0) + 2 * int(t.get("retweetCount") or 0) + int(t.get("bookmarkCount") or 0)


def load_mapping():
    raw = json.loads(MAP.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    return {}


def main():
    tweets = json.loads(TW.read_text(encoding="utf-8"))
    mapping = load_mapping()
    out = {"tweet_count": len(tweets), "groups": {}}

    for name, pats in GROUPS.items():
        regs = [re.compile(p, re.I) for p in pats]
        hits = []
        for t in tweets:
            txt = t.get("text") or ""
            ntx = norm(txt)
            # patterns are Turkish-tolerant enough; test both raw and normalized
            if any(r.search(txt) or r.search(ntx) for r in regs):
                tid = str(t.get("id") or "")
                imgs = mapping.get(tid) or []
                if isinstance(imgs, str):
                    imgs = [imgs]
                hits.append({
                    "id": tid,
                    "date": t.get("createdAt"),
                    "text": txt,
                    "score": score(t),
                    "likes": t.get("likeCount") or 0,
                    "retweets": t.get("retweetCount") or 0,
                    "media": imgs,
                    "pct_mentions": PCT_RE.findall(txt),
                    "rr_mentions": RR_RE.findall(txt),
                })
        hits.sort(key=lambda x: (x["score"], x["date"] or ""), reverse=True)
        pcts = Counter(x for h in hits for x in h["pct_mentions"])
        rrs = Counter(x.lower().replace(" ", "") for h in hits for x in h["rr_mentions"])
        out["groups"][name] = {
            "count": len(hits),
            "media_count": sum(bool(h["media"]) for h in hits),
            "percent_mentions": pcts.most_common(20),
            "rr_mentions": rrs.most_common(20),
            "examples": hits[:40],
        }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# terminalMiraz Kanıt Raporu",
        "",
        f"Kaynak: `{TW.relative_to(ROOT)}` — **{len(tweets)} tweet**.",
        "Bu rapor otomatik metin eşlemesidir; chart yorumu için bağlı görseller ayrıca doğrulanmalıdır.",
        "",
    ]
    for name, g in out["groups"].items():
        lines += [f"## {name}", "", f"- Eşleşen tweet: **{g['count']}**", f"- Görselli tweet: **{g['media_count']}**"]
        if g["percent_mentions"]:
            lines.append("- Yüzde ifadeleri: " + ", ".join(f"`{k}`×{v}" for k, v in g["percent_mentions"][:10]))
        if g["rr_mentions"]:
            lines.append("- R/R ifadeleri: " + ", ".join(f"`{k}`×{v}" for k, v in g["rr_mentions"][:10]))
        lines += ["", "### En güçlü örnekler", ""]
        for h in g["examples"][:12]:
            txt = " ".join((h["text"] or "").split())
            if len(txt) > 500:
                txt = txt[:497] + "..."
            lines.append(f"- **{h['date']} · {h['id']} · skor {h['score']}** — {txt}")
            if h["media"]:
                lines.append("  - Görsel: " + ", ".join(f"`tweetler/gorseller/{x}`" if "/" not in str(x) else f"`{x}`" for x in h["media"][:6]))
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD} and {OUT_JSON}")


if __name__ == "__main__":
    main()
