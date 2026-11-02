"""Pre-render responsive WebP variants for static guest images.

Writes `<image>.w640.webp` / `<image>.w1280.webp` next to each photo under
frontend/public/images/luma-haven (branding excluded) and a manifest of original
widths that frontend/src/utils/responsiveImage.ts uses to build `srcset`.
Re-run after adding or replacing a static photo:

    .venv/bin/python scripts/build_static_image_variants.py
"""
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'frontend' / 'public'
SOURCE = PUBLIC / 'images' / 'luma-haven'
MANIFEST = ROOT / 'frontend' / 'src' / 'data' / 'imageVariants.json'
WIDTHS = (640, 1280)


def main():
    manifest = {}
    for path in sorted(SOURCE.rglob('*')):
        if path.suffix.lower() not in ('.jpg', '.jpeg', '.png') or 'branding' in path.parts:
            continue
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
        widths = [w for w in WIDTHS if w < image.width]
        for width in widths:
            target = path.with_name(f'{path.name}.w{width}.webp')
            variant = image.copy()
            variant.thumbnail((width, width * 10), Image.LANCZOS)
            variant.save(target, format='WEBP', quality=80, method=6)
        manifest['/' + path.relative_to(PUBLIC).as_posix()] = {'width': image.width, 'variants': widths}
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    print(f'{len(manifest)} images, manifest at {MANIFEST.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
