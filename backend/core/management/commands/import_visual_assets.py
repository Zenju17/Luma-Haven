import hashlib
import json
import os
import shutil
from pathlib import Path
from PIL import Image

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from core.models import Hotel, RoomType, VisualAsset

SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class Command(BaseCommand):
    help = 'Discovers, validates, and imports visual assets into managed media storage and database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            required=False,
            help='Path to source visual assets directory (e.g. Luma-Haven_Visual_Assets/ or /app/source_assets/).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate discovery, validation, and mapping without saving files or database records.'
        )
        parser.add_argument(
            '--config',
            type=str,
            default=None,
            help='Path to asset_mapping.json configuration file.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update metadata on existing assets if already imported.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        source_arg = options['source']

        # Determine source directory
        source_dir = self.resolve_source_dir(source_arg)
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Visual Assets Import {'(DRY RUN)' if dry_run else ''} ==="))
        self.stdout.write(f"Source Directory: {source_dir}")

        # Load mapping configuration
        config_path = self.resolve_config_path(options['config'])
        self.stdout.write(f"Configuration File: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        room_type_mappings = config.get('room_type_mappings', {})
        category_folders = config.get('category_folders', {})
        asset_metadata = config.get('asset_metadata', {})

        # Fetch primary hotel
        hotel = Hotel.objects.first()
        if not hotel and not dry_run:
            raise CommandError("No Hotel found in database. Run migrations and seed data before importing assets.")

        # Cache existing room types
        room_types_by_name = {rt.name.lower(): rt for rt in RoomType.objects.all()}

        # Discover image files recursively
        discovered_files = []
        for root, _, files in os.walk(source_dir):
            for file_name in sorted(files):
                ext = os.path.splitext(file_name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_path = Path(root) / file_name
                    rel_path = full_path.relative_to(source_dir)
                    # Ignore full contact sheet from public delivery (it's internal reference)
                    if file_name.startswith('full_visual_contact_sheet'):
                        continue
                    discovered_files.append((full_path, rel_path))

        self.stdout.write(f"Discovered {len(discovered_files)} supported image files.\n")

        # Table Header
        self.stdout.write(f"{'Relative File Path':<35} | {'Category':<12} | {'Room Type':<16} | {'Dimensions':<11} | {'Size (KB)':<10} | {'Status'}")
        self.stdout.write("-" * 115)

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        unassigned_count = 0
        error_count = 0

        for full_path, rel_path in discovered_files:
            rel_str = str(rel_path).replace('\\', '/')
            file_size = full_path.stat().st_size

            # 1. Validate file size
            if file_size > MAX_FILE_SIZE_BYTES:
                self.stdout.write(self.style.ERROR(f"{rel_str:<35} | OVERSIZED ({file_size} bytes > {MAX_FILE_SIZE_BYTES})"))
                error_count += 1
                continue

            # 2. Validate image format and dimensions via Pillow
            try:
                with Image.open(full_path) as img:
                    img_format = img.format
                    width, height = img.size
                    img.verify()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"{rel_str:<35} | CORRUPTED / INVALID IMAGE: {e}"))
                error_count += 1
                continue

            # 3. Compute SHA-256 content hash
            hasher = hashlib.sha256()
            with open(full_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            content_hash = hasher.hexdigest()

            # 4. Resolve Category & Target Room Type
            parts = rel_path.parts
            top_folder = parts[0] if parts else ''
            category = category_folders.get(top_folder, 'OTHER')
            target_room_type = None
            is_unassigned = False

            if category == 'ROOM_TYPE' and len(parts) >= 2:
                folder_room_key = parts[1]
                target_room_name = room_type_mappings.get(folder_room_key)
                if target_room_name:
                    target_room_type = room_types_by_name.get(target_room_name.lower())
                    if not target_room_type and not dry_run:
                        self.stdout.write(self.style.WARNING(f"Room type '{target_room_name}' not found in database!"))
                else:
                    is_unassigned = True
                    unassigned_count += 1

            # 5. Extract metadata from config or sensible defaults
            stem_path = str(rel_path.with_suffix('')).replace('\\', '/')
            meta = (
                asset_metadata.get(rel_str)
                or asset_metadata.get(f"{stem_path}.jpg")
                or asset_metadata.get(f"{stem_path}.png")
                or asset_metadata.get(stem_path)
                or {}
            )
            title = meta.get('title', rel_path.stem.replace('_', ' ').title())
            caption = meta.get('caption', '')
            alt_text = meta.get('alt_text', f"Luma Haven {title}")
            display_order = meta.get('display_order', 1)
            source_type = meta.get('source_type', 'CONCEPT')
            facility_claim = meta.get('facility_claim', '')

            room_label = target_room_type.name if target_room_type else ('(Unassigned)' if is_unassigned else '-')
            dim_str = f"{width}x{height}"
            size_kb = f"{file_size // 1024} KB"

            target_media_rel = f"visual_assets/{rel_str}"

            # Check if asset exists in DB by hash, exact filename, or stem path (e.g. upgraded from .png to .jpg)
            existing = VisualAsset.objects.filter(content_hash=content_hash).first()
            if not existing:
                existing = VisualAsset.objects.filter(category=category, original_filename=rel_str).first()
            if not existing:
                stem_candidates = [f"{stem_path}{ext}" for ext in SUPPORTED_EXTENSIONS]
                existing = VisualAsset.objects.filter(category=category, original_filename__in=stem_candidates).first()


            if existing:
                is_upgrade = (
                    width > existing.width
                    or height > existing.height
                    or content_hash != existing.content_hash
                    or existing.original_filename != rel_str
                )
                if (force or is_upgrade) and not dry_run:
                    # Copy HD image into managed media storage
                    target_media_full = Path(settings.MEDIA_ROOT) / target_media_rel
                    target_media_full.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, target_media_full)

                    # Remove old media file if path/extension changed
                    if existing.image and existing.image.name != target_media_rel:
                        old_file = Path(settings.MEDIA_ROOT) / existing.image.name
                        if old_file.exists() and old_file.is_file():
                            try:
                                old_file.unlink()
                            except OSError:
                                pass

                    existing.image = target_media_rel
                    existing.original_filename = rel_str
                    existing.content_hash = content_hash
                    existing.width = width
                    existing.height = height
                    existing.file_size_bytes = file_size
                    existing.title = title
                    existing.caption = caption
                    existing.alt_text = alt_text
                    existing.display_order = display_order
                    existing.category = category
                    if target_room_type is not None:
                        existing.room_type = target_room_type
                    existing.source_type = source_type
                    existing.facility_claim = facility_claim
                    existing.save()

                    status_text = self.style.WARNING(f'UPGRADED TO HD ({width}x{height})')
                    updated_count += 1
                elif dry_run and (force or (width > 0)):
                    status_text = self.style.WARNING(f'WOULD UPGRADE TO HD ({width}x{height})')
                    updated_count += 1
                else:
                    status_text = self.style.NOTICE('EXISTS (SKIPPED)')
                    skipped_count += 1
            else:
                if dry_run:
                    status_text = self.style.SUCCESS(f'WOULD IMPORT ({width}x{height})')
                    imported_count += 1
                else:
                    target_media_full = Path(settings.MEDIA_ROOT) / target_media_rel
                    target_media_full.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, target_media_full)

                    asset = VisualAsset(
                        hotel=hotel,
                        category=category,
                        room_type=target_room_type,
                        image=target_media_rel,
                        title=title,
                        caption=caption,
                        alt_text=alt_text,
                        display_order=display_order,
                        is_active=True,
                        source_type=source_type,
                        facility_claim=facility_claim,
                        original_filename=rel_str,
                        content_hash=content_hash,
                        file_size_bytes=file_size,
                        width=width,
                        height=height,
                    )
                    asset.save()
                    status_text = self.style.SUCCESS(f'IMPORTED ({width}x{height})')
                    imported_count += 1

            self.stdout.write(f"{rel_str:<35} | {category:<12} | {room_label:<16} | {dim_str:<11} | {size_kb:<10} | {status_text}")


        # Summary Report
        self.stdout.write("-" * 115)
        self.stdout.write(self.style.MIGRATE_HEADING("=== Summary Report ==="))
        self.stdout.write(f"Total Discovered: {len(discovered_files)}")
        self.stdout.write(f"Imported / Planned: {imported_count}")
        self.stdout.write(f"Updated:            {updated_count}")
        self.stdout.write(f"Skipped (Existing): {skipped_count}")
        self.stdout.write(f"Unassigned Rooms:   {unassigned_count} (rooms/deluxe/* and rooms/premier/* pending confirmation)")
        self.stdout.write(f"Errors / Rejected:  {error_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run complete. No files were copied and no database records were created."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nImport successfully completed. Media stored under: {settings.MEDIA_ROOT}"))

    def resolve_source_dir(self, source_arg):
        if source_arg:
            p = Path(source_arg)
            if p.exists() and p.is_dir():
                return p
            raise CommandError(f"Specified source directory does not exist: {source_arg}")

        # Try default locations
        candidates = [
            Path(settings.BASE_DIR) / 'source_assets',
            Path(settings.BASE_DIR).parent / 'Luma-Haven_Visual_Assets',
            Path('/app/source_assets'),
            Path(os.getcwd()) / 'Luma-Haven_Visual_Assets',
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c

        raise CommandError(
            "Could not automatically locate visual assets folder. "
            "Please specify --source /path/to/Luma-Haven_Visual_Assets/"
        )

    def resolve_config_path(self, config_arg):
        if config_arg:
            p = Path(config_arg)
            if p.exists() and p.is_file():
                return p
            raise CommandError(f"Specified config file does not exist: {config_arg}")

        candidates = [
            Path(settings.BASE_DIR) / 'core' / 'asset_mapping.json',
            Path(settings.BASE_DIR) / 'config' / 'asset_mapping.json',
            Path(os.getcwd()) / 'backend' / 'core' / 'asset_mapping.json',
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c

        raise CommandError("Could not locate asset_mapping.json configuration file.")
