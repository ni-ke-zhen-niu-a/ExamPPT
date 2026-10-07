from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pictures(slide):
    return [shape for shape in slide.shapes if shape.shape_type == 13]


def _section_title(manifest: dict, q: int) -> str:
    sections = manifest.get("sections", [])
    if not sections:
        return ""

    # New Question IR format: each section has start_question.
    modern = [s for s in sections if "start_question" in s]
    if modern:
        applicable = [s for s in modern if int(s["start_question"]) <= q]
        if not applicable:
            return ""
        return max(applicable, key=lambda s: int(s["start_question"]))["title"]

    # Legacy format: explicit start/end range.
    for section in sections:
        if int(section["start"]) <= q <= int(section["end"]):
            return section["title"]
    return ""


def _load_question_images(manifest: dict, manifest_path: Path) -> tuple[dict[int, dict], list[str]]:
    qimgs: dict[int, dict] = {}
    violations: list[str] = []

    # New pipeline: scanner already produced one complete image per question.
    if manifest.get("questions"):
        for item in manifest["questions"]:
            q = int(item["number"])
            image_value = item.get("image")
            if not image_value:
                violations.append(f"Q{q}: missing rendered question image")
                continue
            image_path = Path(image_value)
            if not image_path.is_absolute():
                image_path = (manifest_path.parent / image_path).resolve()
            if not image_path.exists():
                violations.append(f"Q{q}: image does not exist: {image_path}")
                continue
            with Image.open(image_path) as im:
                ratio = im.height / im.width
            qimgs[q] = {"path": image_path, "ratio": ratio}
        return qimgs, violations

    # Compatibility path for the original regression manifest.
    source_pptx = manifest.get("source_pptx")
    question_map = manifest.get("question_map")
    if not source_pptx or not question_map:
        return {}, ["Manifest contains neither Question IR images nor legacy question_map."]

    source = Path(source_pptx)
    prs = Presentation(str(source))
    assets = ROOT / "assets" / manifest_path.stem
    assets.mkdir(parents=True, exist_ok=True)

    for q in range(1, int(manifest["question_count"]) + 1):
        refs = question_map.get(str(q))
        if not refs:
            violations.append(f"Q{q}: missing legacy mapping")
            continue
        parts: list[Image.Image] = []
        for slide_no, picture_no in refs:
            pics = _pictures(prs.slides[int(slide_no) - 1])
            if int(picture_no) > len(pics):
                violations.append(f"Q{q}: source picture {slide_no}/{picture_no} missing")
                continue
            parts.append(Image.open(BytesIO(pics[int(picture_no) - 1].image.blob)).convert("RGB"))

        if not parts:
            continue
        width = max(im.width for im in parts)
        height = sum(im.height for im in parts) + max(0, len(parts) - 1) * 8
        merged = Image.new("RGB", (width, height), "white")
        y = 0
        for im in parts:
            if im.width != width:
                new_h = round(im.height * width / im.width)
                im = im.resize((width, new_h), Image.Resampling.LANCZOS)
            merged.paste(im, (0, y))
            y += im.height + 8
        image_path = assets / f"q{q:03d}.png"
        merged.save(image_path)
        qimgs[q] = {"path": image_path, "ratio": merged.height / merged.width}

    return qimgs, violations


def build(
    manifest_path: str | Path,
    rules_path: str | Path | None = None,
    output_pptx: str | Path | None = None,
    qa_json: str | Path | None = None,
) -> dict:
    manifest_path = Path(manifest_path)
    manifest = load_json(manifest_path)
    if rules_path is None:
        rules_path = ROOT.parent / "layout_rules.json"
    rules = load_json(rules_path)

    qimgs, violations = _load_question_images(manifest, manifest_path)
    violations.extend(manifest.get("warnings", []))

    question_count = int(manifest.get("question_count") or len(manifest.get("questions", [])))
    if question_count <= 0:
        violations.append("No questions available.")
        question_count = len(qimgs)

    if output_pptx is None:
        output_pptx = manifest_path.parent / f"{manifest.get('name', 'ExamPPT')}_讲题版.pptx"
    if qa_json is None:
        qa_json = Path(output_pptx).with_suffix(".qa.json")

    layout = rules["layout"]
    slide_cfg = rules["slide"]
    content_limit = slide_cfg["height_in"] - layout["bottom_in"]

    breaks = set(manifest.get("section_break_before", []))
    if not breaks:
        breaks = {
            int(s["start_question"])
            for s in manifest.get("sections", [])
            if "start_question" in s and int(s["start_question"]) > 1
        }

    slides: list[list[int]] = []
    current: list[int] = []
    current_heights: list[float] = []
    used = 0.0

    max_h = content_limit - layout["content_top_in"]
    max_questions = int(layout.get("max_questions_per_slide", 999))
    max_multi_fill = float(layout.get("max_multi_fill_ratio", 1.0))
    long_pair_threshold = float(layout.get("long_pair_threshold_in", 1e9))
    separate_long_pairs = bool(layout.get("separate_long_pairs_in_solution_section", False))

    def flush_current() -> None:
        nonlocal current, current_heights, used
        if current:
            slides.append(current)
        current, current_heights, used = [], [], 0.0

    for q in range(1, question_count + 1):
        if q not in qimgs:
            violations.append(f"Q{q}: unavailable for layout")
            continue

        if q in breaks and current:
            flush_current()

        h = layout["question_width_in"] * qimgs[q]["ratio"]
        if h > max_h:
            violations.append(
                f"Q{q}: intrinsic height {h:.3f}in exceeds content area {max_h:.3f}in; MANUAL_REQUIRED"
            )

        if current:
            prospective = used + layout["gap_in"] + h
            hard_overflow = prospective > max_h
            too_many = len(current) >= max_questions
            too_dense = prospective > max_h * max_multi_fill

            section = _section_title(manifest, q)
            long_pair = (
                separate_long_pairs
                and "解答" in section
                and h >= long_pair_threshold
                and any(x >= long_pair_threshold for x in current_heights)
            )

            if hard_overflow or too_many or too_dense or long_pair:
                flush_current()

        current.append(q)
        current_heights.append(h)
        used += h if len(current) == 1 else layout["gap_in"] + h

    flush_current()

    prs = Presentation()
    prs.slide_width = Inches(slide_cfg["width_in"])
    prs.slide_height = Inches(slide_cfg["height_in"])
    blank = prs.slide_layouts[6]
    qa_slides = []

    for slide_idx, questions in enumerate(slides, 1):
        slide = prs.slides.add_slide(blank)

        title = slide.shapes.add_textbox(Inches(0.35), Inches(0.10), Inches(7.9), Inches(0.40))
        title.name = "HEADER_TITLE"
        p = title.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = manifest.get("name", "ExamPPT")
        run.font.name = rules["header"]["title_font"]
        run.font.size = Pt(rules["header"]["title_pt"])
        run.font.bold = True
        run.font.color.rgb = RGBColor(35, 35, 35)

        section = slide.shapes.add_textbox(Inches(8.1), Inches(0.11), Inches(4.9), Inches(0.36))
        section.name = "HEADER_RANGE"
        p = section.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = _section_title(manifest, questions[0])
        run.font.name = rules["header"]["title_font"]
        run.font.size = Pt(rules["header"]["range_pt"])
        run.font.bold = True
        run.font.color.rgb = RGBColor(70, 70, 70)
        p.alignment = PP_ALIGN.RIGHT

        divider = slide.shapes.add_shape(
            1,
            Inches(0.35),
            Inches(rules["header"]["divider_y_in"]),
            Inches(12.65),
            Inches(0.01),
        )
        divider.name = "HEADER_DIVIDER"
        divider.fill.solid()
        divider.fill.fore_color.rgb = RGBColor(225, 225, 225)
        divider.line.color.rgb = RGBColor(225, 225, 225)

        y = layout["content_top_in"]
        entries = []
        for q in questions:
            height = layout["question_width_in"] * qimgs[q]["ratio"]
            shape = slide.shapes.add_picture(
                str(qimgs[q]["path"]),
                Inches(layout["left_in"]),
                Inches(y),
                width=Inches(layout["question_width_in"]),
            )
            shape.name = f"Q{q:03d}_CONTENT"
            entries.append(
                {
                    "q": q,
                    "top": round(y, 3),
                    "bottom": round(y + height, 3),
                    "height": round(height, 3),
                }
            )
            y += height + layout["gap_in"]

        bottom_margin = slide_cfg["height_in"] - entries[-1]["bottom"]
        if bottom_margin < layout["min_bottom_margin_in"]:
            violations.append(
                f"Slide {slide_idx}: bottom margin {bottom_margin:.3f}in below minimum"
            )
        qa_slides.append(
            {
                "slide": slide_idx,
                "questions": questions,
                "bottom_margin": round(bottom_margin, 3),
                "entries": entries,
            }
        )

    output_pptx = Path(output_pptx)
    output_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_pptx))

    seen = [q for slide in qa_slides for q in slide["questions"]]
    expected = list(range(1, question_count + 1))
    if seen != expected:
        violations.append(f"Question order/coverage mismatch: {seen}")

    for q in breaks:
        containing = [s for s in qa_slides if q in s["questions"]]
        if containing and containing[0]["questions"][0] != q:
            violations.append(f"Q{q}: section does not start on a new slide")

    # Stable de-duplication keeps the report readable.
    violations = list(dict.fromkeys(violations))
    report = {
        "status": "PASS" if not violations else "MANUAL_REQUIRED",
        "output": str(output_pptx),
        "slide_count": len(qa_slides),
        "question_count": question_count,
        "fixed_question_width_in": layout["question_width_in"],
        "questions": seen,
        "slides": qa_slides,
        "violations": violations,
    }

    qa_json = Path(qa_json)
    qa_json.parent.mkdir(parents=True, exist_ok=True)
    qa_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
