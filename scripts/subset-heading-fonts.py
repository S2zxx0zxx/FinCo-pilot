"""Reproduce/check Open Runde subsets without removing original font coverage.

Requires fonttools==4.61.1 and brotli. Run from any directory:
  python3 scripts/subset-heading-fonts.py       # regenerate derived assets/CSS
  python3 scripts/subset-heading-fonts.py --check  # cmap/outline/advance proof
Original public/fonts/open-runde files and OFL.txt are never modified.
"""
import argparse
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend/public/fonts/open-runde"
OUTPUT = ROOT / "frontend/src/styles/fonts"


def latin(codepoint: int) -> bool:
    return (codepoint <= 0x24F or 0x1E00 <= codepoint <= 0x1EFF
            or 0x2000 <= codepoint <= 0x206F or 0x20A0 <= codepoint <= 0x20CF
            or 0x2100 <= codepoint <= 0x214F or codepoint in (0xFEFF, 0xFFFD))


def europe(codepoint: int) -> bool:
    return (0x370 <= codepoint <= 0x52F or 0x1F00 <= codepoint <= 0x1FFF
            or 0x2DE0 <= codepoint <= 0x2DFF or 0xA640 <= codepoint <= 0xA69F)


def partitions(codepoints: set[int]) -> dict[str, set[int]]:
    return {
        "latin": {cp for cp in codepoints if latin(cp)},
        "europe": {cp for cp in codepoints if not latin(cp) and europe(cp)},
        "other": {cp for cp in codepoints if not latin(cp) and not europe(cp)},
    }


def unicode_range(values: set[int]) -> str:
    codepoints = sorted(values)
    start = last = codepoints[0]
    ranges = []
    for cp in codepoints[1:] + [None]:
        if cp is not None and cp == last + 1:
            last = cp
            continue
        ranges.append(f"U+{start:X}" + (f"-{last:X}" if start != last else ""))
        start = last = cp
    return ",".join(ranges)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    css = []
    for file in sorted(SOURCE.glob("*.woff2")):
        original = TTFont(file, recalcTimestamp=False)
        cmap = original.getBestCmap()
        groups = partitions(set(cmap))
        assert set.union(*groups.values()) == set(cmap)
        weight = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700}[file.stem.rsplit("-", 1)[1]]
        for group, codepoints in groups.items():
            if not codepoints:
                continue
            destination = OUTPUT / f"{file.stem}-{group}.woff2"
            if not args.check:
                font = TTFont(file, recalcTimestamp=False)
                options = subset.Options()
                options.layout_features = ["*"]
                options.name_IDs = ["*"]
                options.name_languages = ["*"]
                options.notdef_outline = True
                options.recommended_glyphs = True
                options.glyph_names = True
                sub = subset.Subsetter(options=options)
                sub.populate(unicodes=codepoints)
                sub.subset(font)
                font.save(destination)
            derived = TTFont(destination)
            derived_map = derived.getBestCmap()
            assert set(derived_map) == codepoints, destination
            original_glyphs, derived_glyphs = original.getGlyphSet(), derived.getGlyphSet()
            for cp in codepoints:
                source_glyph, derived_glyph = cmap[cp], derived_map[cp]
                assert original["hmtx"][source_glyph] == derived["hmtx"][derived_glyph], (destination, cp)
                source_pen = DecomposingRecordingPen(original_glyphs)
                derived_pen = DecomposingRecordingPen(derived_glyphs)
                original_glyphs[source_glyph].draw(source_pen)
                derived_glyphs[derived_glyph].draw(derived_pen)
                assert source_pen.value == derived_pen.value, (destination, cp)
            css.append("@font-face { font-family: 'Open Runde'; src: url('./fonts/"
                       + destination.name + "') format('woff2'); font-weight: " + str(weight)
                       + "; font-display: swap; unicode-range: " + unicode_range(codepoints) + "; }")
        print(f"{file.name}: preserved {len(cmap)} codepoints, outlines and advances")
    if not args.check:
        style = ROOT / "frontend/src/styles/spaceui.css"
        text = style.read_text()
        start, end = text.index("@font-face"), text.index(":root")
        style.write_text(text[:start] + "\n".join(css) + "\n\n" + text[end:])


if __name__ == "__main__":
    main()
