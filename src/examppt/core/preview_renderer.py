from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SLIDE_W = 1600
SLIDE_H = 900
PX_PER_IN = 120.0


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            Path(r"C:\Windows\Fonts\msyhbd.ttc"),
            Path(r"C:\Windows\Fonts\simhei.ttf"),
        ]
    candidates += [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _section_title(manifest: dict, question: int) -> str:
    sections = manifest.get("sections", [])
    modern = [s for s in sections if "start_question" in s]
    if modern:
        applicable = [s for s in modern if int(s["start_question"]) <= question]
        if applicable:
            return max(applicable, key=lambda s: int(s["start_question"]))["title"]
        return ""

    for section in sections:
        if int(section["start"]) <= question <= int(section["end"]):
            return section["title"]
    return ""


def render_slide_previews(
    manifest_path: str | Path,
    qa_json: str | Path,
    output_dir: str | Path,
) -> list[str]:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa = json.loads(Path(qa_json).read_text(encoding="utf-8"))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    question_images: dict[int, Path] = {}
    for item in manifest.get("questions", []):
        image = item.get("image")
        if not image:
            continue
        p = Path(image)
        if not p.is_absolute():
            p = (manifest_path.parent / p).resolve()
        question_images[int(item["number"])] = p

    title_font = _font(31, bold=True)
    section_font = _font(25, bold=True)
    output_files: list[str] = []

    for slide in qa.get("slides", []):
        canvas = Image.new("RGB", (SLIDE_W, SLIDE_H), "white")
        draw = ImageDraw.Draw(canvas)
        first_q = int(slide["questions"][0])

        title = manifest.get("name", "ExamPPT")
        draw.text((42, 17), title, font=title_font, fill=(35, 35, 35))

        section = _section_title(manifest, first_q)
        if section:
            bbox = draw.textbbox((0, 0), section, font=section_font)
            tw = bbox[2] - bbox[0]
            draw.text((SLIDE_W - 42 - tw, 19), section, font=section_font, fill=(70, 70, 70))

        yline = round(0.55 * PX_PER_IN)
        draw.line((42, yline, SLIDE_W - 40, yline), fill=(225, 225, 225), width=2)

        for entry in slide.get("entries", []):
            q = int(entry["q"])
            image_path = Path(entry["image"]) if entry.get("image") else question_images.get(q)
            if image_path and not image_path.is_absolute():
                image_path = (manifest_path.parent / image_path).resolve()
            if not image_path or not image_path.exists():
                continue
            with Image.open(image_path) as im:
                im = im.convert("RGB")
                width = round(12.633 * PX_PER_IN)
                height = max(1, round(width * im.height / im.width))
                im = im.resize((width, height), Image.Resampling.LANCZOS)
                x = round(0.35 * PX_PER_IN)
                y = round(float(entry["top"]) * PX_PER_IN)
                canvas.paste(im, (x, y))

        out = output_dir / f"slide_{int(slide['slide']):03d}.png"
        canvas.save(out, optimize=True)
        output_files.append(str(out))

    return output_files
