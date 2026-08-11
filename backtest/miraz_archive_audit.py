#!/usr/bin/env python3
"""@tradermiraz arşivinden terminalMiraz davranışları için kanıt özeti üretir.

Bu script strateji kuralı icat etmez. tweetler.json + tweet_gorsel.json içinden
kritik ifadeleri sayar, yüksek-etkileşimli örnekleri ve bağlı chart dosyalarını
raporlar. Amaç canlı klon kurallarını kanıta bağlamaktır.
"""
from __future__ import annotations

import json
import re
import hashlib
import struct
from collections import Counter
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TW = ROOT / "tweetler" / "tweetler.json"
MAP = ROOT / "tweetler" / "tweet_gorsel.json"
OUT_MD = ROOT / "tweetler" / "TERMINALMIRAZ_EVIDENCE.md"
OUT_JSON = ROOT / "tweetler" / "terminalmiraz_evidence.json"
IMAGE_MANIFEST = ROOT / "tweetler" / "terminalmiraz_image_manifest.json"
IMAGE_DIR = ROOT / "tweetler" / "gorseller"

GROUPS = {
    "terminal": [r"terminal\s*miraz", r"terminal"],
    "trigger": [r"trend\s*k[ıi]r[ıi]l", r"yeşil\s*daire", r"teyit", r"onay"],
    "volume_close": [r"hacimli\s*kapan", r"hacim.*kapan", r"kapan.*hacim"],
    "close_invalidation": [r"alt[ıi]nda\s+kapan", r"[üu]st[üu]nde\s+kapan", r"kapan[ıi]ş.*iptal", r"ge[çc]ersiz"],
    "partial_be": [r"k[âa]r\s*al", r"kar\s*al", r"giri[şs]e\s*stop", r"stop.*giri[şs]", r"breakeven", r"break\s*even", r"risksiz"],
    "rr": [r"\b1\s*[rR]\b", r"\b2\s*[rR]\b", r"1\s*[:/]\s*2", r"risk\s*/?\s*reward", r"risk.*reward"],
    # Tek başına "dengeli" çok sayıda alakasız sonuç üretir. Risk modu ancak
    # üçlü sınıflandırma veya açık R hedefi aynı bağlamdaysa kanıt sayılır.
    "risk_modes": [
        r"g[üu]venli.{0,160}dengeli.{0,160}riskli",
        r"g[üu]venli\s*:\s*\+?\d+(?:[.,]\d+)?\s*r",
        r"dengeli\s*:\s*\+?\d+(?:[.,]\d+)?\s*r",
        r"riskli\s*:\s*\+?\d+(?:[.,]\d+)?\s*r",
    ],
    "harmonic": [r"harmonik", r"gartley", r"butterfly", r"kelebek", r"bat\b", r"crab", r"yenge[çc]", r"cypher", r"shark", r"prz"],
    "retest": [r"re[- ]?test", r"geri\s*test", r"k[ıi]r[ıi]l.*test"],
    "terminal_statuses": [r"rafa\s*kalk", r"expired", r"cancelled", r"late", r"no\s*entry", r"filtrelendi"],
    "quality_engine": [r"kalite\s*motoru", r"kalite\s*kontrol", r"işleme\s*değer", r"işlem\s*dışı"],
    "pa_harmonic_split": [r"price\s*action.{0,100}harmonik", r"harmonik.{0,100}price\s*action", r"pa\s*/\s*harmonik"],
    "result_journal": [r"tp\s*ise\s*tp", r"stop\s*ise\s*stop", r"sonu[çc].*hafıza", r"işlem\s*ge[çc]mi[şs]", r"sonu[çc]lanan\s*i[şs]lem"],
    "timeframes_htf": [r"higher\s*time", r"lower\s*time", r"zaman\s*dilimi", r"timeframe", r"t[üu]mdengelim"],
    "automation_execution": [r"otomatik.*i[şs]lem", r"otonom", r"execution", r"pozisyon\s*takip", r"kendi\s*kurallar"],
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


def image_size(path: Path) -> tuple[int | None, int | None]:
    """PNG/JPEG boyutunu bağımlılık eklemeden oku."""
    with path.open("rb") as fh:
        head = fh.read(24)
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">II", head[16:24])
        if head[:2] != b"\xff\xd8":
            return None, None
        fh.seek(2)
        while True:
            marker_start = fh.read(1)
            if not marker_start:
                return None, None
            if marker_start != b"\xff":
                continue
            marker = fh.read(1)
            while marker == b"\xff":
                marker = fh.read(1)
            if marker in {bytes([x]) for x in range(0xC0, 0xC4)} | {bytes([x]) for x in range(0xC5, 0xC8)} | {bytes([x]) for x in range(0xC9, 0xCC)} | {bytes([x]) for x in range(0xCD, 0xD0)}:
                fh.read(3)
                height, width = struct.unpack(">HH", fh.read(4))
                return width, height
            length_raw = fh.read(2)
            if len(length_raw) != 2:
                return None, None
            length = struct.unpack(">H", length_raw)[0]
            fh.seek(max(0, length - 2), 1)


def build_image_manifest(mapping: dict) -> dict:
    refs: dict[str, list[str]] = defaultdict(list)
    reference_count = 0
    for tweet_id, value in mapping.items():
        names = [value] if isinstance(value, str) else (value or [])
        for name in names:
            filename = Path(str(name)).name
            refs[filename].append(tweet_id)
            reference_count += 1

    images = []
    content_hashes: dict[str, list[str]] = defaultdict(list)
    for path in sorted(IMAGE_DIR.iterdir()):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        width, height = image_size(path)
        content_hashes[digest].append(path.name)
        images.append({
            "file": path.name,
            "format": path.suffix.lower().lstrip("."),
            "bytes": path.stat().st_size,
            "width": width,
            "height": height,
            "sha256": digest,
            "tweet_ids": refs.get(path.name, []),
            # Semantik chart yorumu yalnız doğrulanmış bir görsel inceleme
            # aşamasında doldurulur; dosya envanteri bunu uydurmaz.
            "visual_review": {"status": "pending", "labels": [], "notes": ""},
        })

    disk_names = {x["file"] for x in images}
    referenced_names = set(refs)
    return {
        "reference_count": reference_count,
        "unique_referenced_files": len(referenced_names),
        "disk_file_count": len(images),
        "missing_files": sorted(referenced_names - disk_names),
        "orphan_files": sorted(disk_names - referenced_names),
        "multiply_referenced_files": {
            name: ids for name, ids in sorted(refs.items()) if len(ids) > 1
        },
        "duplicate_content": [names for names in content_hashes.values() if len(names) > 1],
        "images": images,
    }


def main():
    tweets = json.loads(TW.read_text(encoding="utf-8"))
    mapping = load_mapping()
    manifest = build_image_manifest(mapping)
    IMAGE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    out = {
        "tweet_count": len(tweets),
        "archive_integrity": {k: v for k, v in manifest.items() if k != "images"},
        "groups": {},
    }

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
            "all_matches": [
                {"id": h["id"], "date": h["date"], "media": h["media"]}
                for h in hits
            ],
        }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# terminalMiraz Kanıt Raporu",
        "",
        f"Kaynak: `{TW.relative_to(ROOT)}` — **{len(tweets)} tweet**.",
        f"Medya: **{manifest['reference_count']} referans / {manifest['disk_file_count']} benzersiz dosya**.",
        "Bu rapor otomatik metin eşlemesidir; chart yorumu için bağlı görseller ayrıca doğrulanmalıdır. "
        "Doğrulanmamış görseller manifestte `visual_review.status=pending` kalır.",
        "",
        "## Arşiv bütünlüğü",
        "",
        f"- Eksik dosya: **{len(manifest['missing_files'])}**",
        f"- Sahipsiz dosya: **{len(manifest['orphan_files'])}**",
        f"- Birden fazla kez referanslanan dosya: **{len(manifest['multiply_referenced_files'])}**",
        f"- Aynı içeriğe sahip dosya grubu: **{len(manifest['duplicate_content'])}**",
        f"- Tam görsel manifesti: `{IMAGE_MANIFEST.relative_to(ROOT)}`",
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
    print(f"Wrote {OUT_MD}, {OUT_JSON} and {IMAGE_MANIFEST}")


if __name__ == "__main__":
    main()
