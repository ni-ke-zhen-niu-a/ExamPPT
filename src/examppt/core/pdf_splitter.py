from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageChops
import numpy as np

from .question_ir import PageSegment, QuestionAnchor, QuestionRegion, ScanResult, Section


QUESTION_RE = re.compile(r"^(\d{1,3})[\.．、](?:\s|\S)")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+)[、\.．]\s*(.+)$")


def _group_lines(words: list[dict], y_tol: float = 2.5) -> list[dict]:
    if not words:
        return []
    words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))
    groups: list[list[dict]] = []
    for w in words:
        if not groups:
            groups.append([w])
            continue
        prev_top = sum(float(x["top"]) for x in groups[-1]) / len(groups[-1])
        if abs(float(w["top"]) - prev_top) <= y_tol:
            groups[-1].append(w)
        else:
            groups.append([w])

    lines = []
    for group in groups:
        group.sort(key=lambda w: float(w["x0"]))
        lines.append(
            {
                "text": "".join(str(w["text"]) for w in group).strip(),
                "x0": min(float(w["x0"]) for w in group),
                "x1": max(float(w["x1"]) for w in group),
                "top": min(float(w["top"]) for w in group),
                "bottom": max(float(w["bottom"]) for w in group),
            }
        )
    return lines


def _detect_candidates(pdf_path: Path) -> tuple[list[dict], list[QuestionAnchor], list[dict]]:
    pages: list[dict] = []
    candidates: list[QuestionAnchor] = []
    section_candidates: list[dict] = []

    with pdfplumber.open(pdf_path) as doc:
        for page_no, page in enumerate(doc.pages, 1):
            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=2,
                keep_blank_chars=False,
                use_text_flow=False,
            )
            lines = _group_lines(words)
            pages.append(
                {
                    "page": page_no,
                    "width": float(page.width),
                    "height": float(page.height),
                    "text_word_count": len(words),
                }
            )

            for line in lines:
                text = line["text"]
                qmatch = QUESTION_RE.match(text)
                if qmatch and line["x0"] <= float(page.width) * 0.35:
                    number = int(qmatch.group(1))
                    left_score = max(0.0, 1.0 - line["x0"] / max(float(page.width) * 0.35, 1.0))
                    candidates.append(
                        QuestionAnchor(
                            number=number,
                            page=page_no,
                            x0=line["x0"],
                            top=line["top"],
                            bottom=line["bottom"],
                            text=text[:200],
                            confidence=round(0.85 + 0.15 * left_score, 3),
                        )
                    )

                smatch = SECTION_RE.match(text)
                if smatch and "题" in smatch.group(2) and line["x0"] <= float(page.width) * 0.4:
                    section_candidates.append(
                        {
                            "title": text[:80],
                            "page": page_no,
                            "top": line["top"],
                        }
                    )

    return pages, candidates, section_candidates


def _select_sequential_anchors(candidates: list[QuestionAnchor]) -> tuple[list[QuestionAnchor], list[str]]:
    ordered = sorted(candidates, key=lambda a: (a.page, a.top, a.x0))
    warnings: list[str] = []

    starts = [i for i, a in enumerate(ordered) if a.number == 1]
    if not starts:
        return [], ["No question 1 anchor detected; manual boundary editing required."]

    best: list[QuestionAnchor] = []
    for start in starts:
        seq: list[QuestionAnchor] = []
        expected = 1
        for a in ordered[start:]:
            if a.number == expected:
                seq.append(a)
                expected += 1
            elif a.number > expected:
                continue
        if len(seq) > len(best):
            best = seq

    if not best:
        return [], ["Question sequence detection failed."]

    numbers = [a.number for a in best]
    if numbers != list(range(1, len(best) + 1)):
        warnings.append(f"Non-contiguous question sequence detected: {numbers}")

    # Warn when a plausible next number existed but was not selected.
    max_candidate = max((a.number for a in candidates if a.number < 200), default=len(best))
    if max_candidate > len(best):
        warnings.append(
            f"Detected sequence stops at Q{len(best)}, while later numeric anchors exist up to {max_candidate}; review required."
        )

    return best, warnings


def _detect_sections(section_candidates: list[dict], anchors: list[QuestionAnchor]) -> list[Section]:
    sections: list[Section] = []
    for s in sorted(section_candidates, key=lambda x: (x["page"], x["top"])):
        next_q = next(
            (
                a
                for a in anchors
                if (a.page > s["page"]) or (a.page == s["page"] and a.top > s["top"])
            ),
            None,
        )
        if next_q is None:
            continue
        if sections and sections[-1].start_question == next_q.number:
            continue
        sections.append(
            Section(
                title=s["title"],
                start_question=next_q.number,
                page=s["page"],
                top=s["top"],
            )
        )
    return sections


def _build_regions(
    pages: list[dict],
    anchors: list[QuestionAnchor],
    sections: list[Section] | None = None,
    horizontal_margin: float = 44.0,
    continuation_top: float = 34.0,
    continuation_bottom: float = 48.0,
    anchor_pad_top: float = 4.0,
    before_next_pad: float = 4.0,
) -> list[QuestionRegion]:
    by_page = {p["page"]: p for p in pages}
    regions: list[QuestionRegion] = []

    for i, anchor in enumerate(anchors):
        nxt = anchors[i + 1] if i + 1 < len(anchors) else None
        end_page = nxt.page if nxt else pages[-1]["page"]
        segs: list[PageSegment] = []

        for page_no in range(anchor.page, end_page + 1):
            meta = by_page[page_no]
            width, height = meta["width"], meta["height"]
            x0 = min(horizontal_margin, anchor.x0)
            x1 = width - horizontal_margin

            if page_no == anchor.page:
                top = max(0.0, anchor.top - anchor_pad_top)
            else:
                top = continuation_top

            if nxt and page_no == nxt.page:
                boundary_top = nxt.top
                if sections:
                    markers = [
                        sec.top
                        for sec in sections
                        if sec.start_question == nxt.number and sec.page == page_no
                    ]
                    if markers:
                        boundary_top = min(boundary_top, min(markers))
                bottom = max(top + 1.0, boundary_top - before_next_pad)
            else:
                bottom = height - continuation_bottom

            if bottom > top + 1:
                segs.append(
                    PageSegment(
                        page=page_no,
                        x0=round(x0, 2),
                        top=round(top, 2),
                        x1=round(x1, 2),
                        bottom=round(bottom, 2),
                    )
                )

        regions.append(
            QuestionRegion(
                number=anchor.number,
                anchor=anchor,
                segments=segs,
                cross_page=len(segs) > 1,
                confidence=anchor.confidence,
            )
        )

    return regions


def _trim_vertical_white(image: Image.Image, threshold: int = 248, padding: int = 10) -> Image.Image:
    rgb = image.convert("RGB")
    # Difference from white; bbox finds meaningful non-white pixels.
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > (255 - threshold) else 0)
    bbox = mask.getbbox()
    if not bbox:
        return rgb
    _, y0, _, y1 = bbox
    y0 = max(0, y0 - padding)
    y1 = min(rgb.height, y1 + padding)
    return rgb.crop((0, y0, rgb.width, y1))


def _compact_blank_rows(
    image: Image.Image,
    threshold: int = 248,
    min_blank_run: int = 20,
    keep_blank_rows: int = 10,
) -> Image.Image:
    """Collapse only long completely blank horizontal bands.

    This changes whitespace, never the scale of visible source content.
    """
    arr = np.asarray(image.convert("RGB"))
    ink = np.any(arr < threshold, axis=2)
    has_ink = ink.any(axis=1)
    chunks = []
    i = 0
    n = len(has_ink)
    while i < n:
        j = i + 1
        while j < n and has_ink[j] == has_ink[i]:
            j += 1
        if has_ink[i]:
            chunks.append(arr[i:j])
        else:
            run = j - i
            if run < min_blank_run:
                chunks.append(arr[i:j])
            else:
                keep = min(keep_blank_rows, run)
                before = keep // 2
                after = keep - before
                chunks.append(np.concatenate([arr[i:i+before], arr[j-after:j]], axis=0))
        i = j
    if not chunks:
        return image.convert("RGB")
    return Image.fromarray(np.concatenate(chunks, axis=0))


def render_questions(
    pdf_path: str | Path,
    result: ScanResult,
    output_dir: str | Path,
    dpi: int = 180,
    join_gap_px: int = 8,
) -> ScanResult:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scale = dpi / 72.0
    doc = pdfium.PdfDocument(str(pdf_path))

    for q in result.questions:
        images: list[Image.Image] = []
        target_width: int | None = None

        for seg in q.segments:
            page = doc[seg.page - 1]
            page_w, page_h = page.get_size()
            crop = (
                max(0.0, seg.x0),
                max(0.0, page_h - seg.bottom),
                max(0.0, page_w - seg.x1),
                max(0.0, seg.top),
            )
            bitmap = page.render(scale=scale, crop=crop)
            image = bitmap.to_pil().convert("RGB")
            image = _trim_vertical_white(image)

            if target_width is None:
                target_width = image.width
            elif image.width != target_width:
                new_h = max(1, round(image.height * target_width / image.width))
                image = image.resize((target_width, new_h), Image.Resampling.LANCZOS)
            images.append(image)

        if not images:
            result.warnings.append(f"Q{q.number}: no renderable segment.")
            result.status = "MANUAL_REQUIRED"
            continue

        width = max(im.width for im in images)
        height = sum(im.height for im in images) + join_gap_px * (len(images) - 1)
        merged = Image.new("RGB", (width, height), "white")
        y = 0
        for im in images:
            merged.paste(im, (0, y))
            y += im.height + join_gap_px

        merged = _compact_blank_rows(merged)
        merged = _trim_vertical_white(merged)

        image_path = output_dir / f"q{q.number:03d}.png"
        merged.save(image_path, optimize=True)
        q.image = str(image_path)

    return result


def scan_pdf(
    pdf_path: str | Path,
    output_dir: str | Path | None = None,
    render: bool = True,
    dpi: int = 180,
) -> ScanResult:
    pdf_path = Path(pdf_path).resolve()
    pages, candidates, section_candidates = _detect_candidates(pdf_path)
    anchors, warnings = _select_sequential_anchors(candidates)

    if not anchors:
        return ScanResult(
            source_pdf=str(pdf_path),
            name=pdf_path.stem,
            pages=pages,
            questions=[],
            sections=[],
            warnings=warnings,
            status="MANUAL_REQUIRED",
        )

    sections = _detect_sections(section_candidates, anchors)
    regions = _build_regions(pages, anchors, sections=sections)

    status = "PASS"
    if warnings:
        status = "MANUAL_REQUIRED"

    result = ScanResult(
        source_pdf=str(pdf_path),
        name=pdf_path.stem,
        pages=pages,
        questions=regions,
        sections=sections,
        warnings=warnings,
        status=status,
    )

    if render:
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_examppt"
        result = render_questions(pdf_path, result, Path(output_dir) / "questions", dpi=dpi)

    return result


def save_scan_result(result: ScanResult, manifest_path: str | Path) -> None:
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
