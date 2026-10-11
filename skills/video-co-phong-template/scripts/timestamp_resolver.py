#!/usr/bin/env python3
"""
timestamp_resolver.py — Gắn start_hint/end_hint chính xác vào creative_plan.toml

Sau khi LLM đã viết scene_intents (bao gồm spoken_text và visual_intent),
script này khớp spoken_text của mỗi scene với [[words]] trong transcript
để tìm timestamp chính xác từ giọng đọc thực tế.

Thuật toán: Sliding window fuzzy match — chuẩn hóa chuỗi (lowercase, bỏ
dấu câu), tìm cửa sổ từ trong transcript khớp tốt nhất với spoken_text
của scene, lấy start của từ đầu và end của từ cuối.

Dùng:
    python skills/video-co-phong-template/scripts/timestamp_resolver.py \\
        --creative-plan jobs/<job_id>/source/creative_plan.toml \\
        --transcript   jobs/<job_id>/source/transcript_word_level.toml \\
        --output       jobs/<job_id>/source/creative_plan.toml  # ghi đè hoặc file mới
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


# ─── Chuẩn hoá ───────────────────────────────────────────────────────────────

_STRIP_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(text: str) -> list[str]:
    """Lowercase + bỏ dấu câu, trả về list token."""
    return _STRIP_RE.sub("", text.lower()).split()


# ─── Fuzzy match bằng sliding window ────────────────────────────────────────

def match_score(query_tokens: list[str], window_tokens: list[str]) -> float:
    """Tỉ lệ token giống nhau giữa query và window (0.0 – 1.0)."""
    if not query_tokens or not window_tokens:
        return 0.0
    matched = sum(1 for a, b in zip(query_tokens, window_tokens) if a == b)
    return matched / max(len(query_tokens), len(window_tokens))


def find_best_window(
    query_tokens: list[str],
    word_records: list[dict[str, Any]],
    min_score: float = 0.5,
) -> tuple[float, float] | None:
    """
    Tìm cửa sổ trong word_records khớp tốt nhất với query_tokens.
    Trả về (start, end) tính bằng giây, hoặc None nếu không tìm được.
    """
    n = len(word_records)
    q = len(query_tokens)
    if q == 0 or n == 0:
        return None

    best_score = -1.0
    best_start_idx = 0
    best_end_idx = min(q, n) - 1

    # Thử các cửa sổ có độ rộng từ 50% đến 150% số token của query
    lo = max(1, q // 2)
    hi = min(n, q + q // 2 + 3)

    for window_size in range(lo, hi + 1):
        # Biến thể từ: record có thể chứa field 'word' hoặc 'text'
        for start in range(n - window_size + 1):
            window_words = [
                normalize(
                    str(word_records[start + i].get("word")
                        or word_records[start + i].get("text", ""))
                )[0] if normalize(
                    str(word_records[start + i].get("word")
                        or word_records[start + i].get("text", ""))
                ) else ""
                for i in range(window_size)
            ]
            score = match_score(query_tokens, window_words)
            if score > best_score:
                best_score = score
                best_start_idx = start
                best_end_idx = start + window_size - 1

    if best_score < min_score:
        return None

    start_time = float(word_records[best_start_idx].get("start", 0.0))
    end_time = float(word_records[best_end_idx].get("end", start_time))
    return start_time, end_time


# ─── TOML writer ────────────────────────────────────────────────────────────

def _toml_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
        return f"[{items}]"
    # string — dùng triple-quote nếu chứa newline, nếu không thì quote đơn
    s = str(value)
    if "\n" in s or '"""' not in s and len(s) > 60:
        escaped = s.replace('"""', "'''")
        return f'"""{escaped}"""'
    escaped = s.replace('"', '\\"')
    return f'"{escaped}"'


def write_creative_plan(
    plan: dict[str, Any],
    scenes_updated: list[dict[str, Any]],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        # metadata
        meta = plan.get("metadata") or {}
        f.write("[metadata]\n")
        for k, v in meta.items():
            f.write(f"{k} = {_toml_str(v)}\n")
        f.write("\n")

        # creative
        creative = plan.get("creative") or {}
        if creative:
            f.write("[creative]\n")
            for k, v in creative.items():
                f.write(f"{k} = {_toml_str(v)}\n")
            f.write("\n")

        # voiceover
        vo = plan.get("voiceover") or {}
        if vo:
            f.write("[voiceover]\n")
            for k, v in vo.items():
                f.write(f"{k} = {_toml_str(v)}\n")
            f.write("\n")

        # scene_intents
        for sc in scenes_updated:
            f.write("[[scene_intents]]\n")
            for k, v in sc.items():
                f.write(f"{k} = {_toml_str(v)}\n")
            f.write("\n")

        # text_overlays (nếu có)
        for overlay in plan.get("text_overlays") or []:
            f.write("[[text_overlays]]\n")
            for k, v in overlay.items():
                f.write(f"{k} = {_toml_str(v)}\n")
            f.write("\n")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gắn timestamp chính xác vào creative_plan.toml từ transcript."
    )
    parser.add_argument(
        "--creative-plan", type=Path, required=True,
        help="Path đến creative_plan.toml (đã có spoken_text và visual_intent)",
    )
    parser.add_argument(
        "--transcript", type=Path, required=True,
        help="Path đến transcript_word_level.toml",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path đầu ra (có thể ghi đè creative_plan.toml gốc)",
    )
    parser.add_argument(
        "--min-score", type=float, default=0.5,
        help="Ngưỡng match tối thiểu (0-1). Mặc định: 0.5",
    )
    args = parser.parse_args()

    for p, name in [(args.creative_plan, "creative_plan"), (args.transcript, "transcript")]:
        if not p.exists():
            print(f"Lỗi: Không tìm thấy {name} tại {p}", file=sys.stderr)
            sys.exit(1)

    with open(args.creative_plan, "rb") as f:
        plan = tomllib.load(f)
    with open(args.transcript, "rb") as f:
        transcript = tomllib.load(f)

    words: list[dict[str, Any]] = transcript.get("words") or []
    meta = transcript.get("metadata") or {}
    total_duration = float(meta.get("duration_seconds") or 0.0)

    if not words:
        print("Lỗi: Không tìm thấy [[words]] trong transcript.", file=sys.stderr)
        sys.exit(1)

    scenes: list[dict[str, Any]] = list(plan.get("scene_intents") or [])
    if not scenes:
        print("Lỗi: Không tìm thấy [[scene_intents]] trong creative_plan.", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] {len(scenes)} scenes · {len(words)} words trong transcript")
    print()

    updated_scenes: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for sc in scenes:
        sc_id = sc.get("id", "?")
        spoken = str(sc.get("spoken_text") or "")
        query_tokens = normalize(spoken)

        result = find_best_window(query_tokens, words, min_score=args.min_score)

        sc_new = dict(sc)  # shallow copy để không sửa gốc
        if result:
            start, end = result
            sc_new["start_hint"] = round(start, 3)
            sc_new["end_hint"] = round(end, 3)
            duration = round(end - start, 1)
            print(f"  ✓ {sc_id}: {start:.2f}s → {end:.2f}s  ({duration}s)")
        else:
            # Giữ nguyên start_hint/end_hint nếu LLM đã ước tính
            unmatched.append(sc_id)
            start = float(sc.get("start_hint") or 0.0)
            end = float(sc.get("end_hint") or 0.0)
            print(f"  ✗ {sc_id}: KHÔNG KHỚP — giữ nguyên hint ({start:.2f}s → {end:.2f}s)", file=sys.stderr)

        updated_scenes.append(sc_new)

    # Snap: tránh khoảng trống giữa các cảnh
    for i in range(1, len(updated_scenes)):
        prev_end = float(updated_scenes[i - 1].get("end_hint") or 0.0)
        curr_start = float(updated_scenes[i].get("start_hint") or 0.0)
        if curr_start < prev_end:
            updated_scenes[i]["start_hint"] = prev_end

    # Kéo dài cảnh cuối đến hết audio
    if updated_scenes and total_duration > 0:
        last_end = float(updated_scenes[-1].get("end_hint") or 0.0)
        if last_end < total_duration:
            updated_scenes[-1]["end_hint"] = round(total_duration, 3)
            print(f"\n  → Kéo dài cảnh cuối đến {total_duration:.2f}s (hết audio)")

    write_creative_plan(plan, updated_scenes, args.output)

    print()
    if unmatched:
        print(f"[CẢNH BÁO] {len(unmatched)} scene không khớp transcript: {unmatched}")
        print("  → Kiểm tra lại spoken_text của các scene này so với transcript thực tế.")
    print(f"[OK] Đã gắn timestamp → {args.output}")


if __name__ == "__main__":
    main()
