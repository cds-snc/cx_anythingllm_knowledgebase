#!/usr/bin/env python3
"""Convert PDF, DOCX, and XLSX files in documents/ to markdown in docs/corpus-md/.

Uses a manifest file to track source file hashes. Only converts files that are
new or have changed since last conversion. Existing manually-created markdown
files are preserved by bootstrapping their manifest entries on first run.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from markitdown import MarkItDown

DOCUMENTS_DIR = Path("documents")
CORPUS_DIR = Path("docs/corpus-md")
MANIFEST_PATH = CORPUS_DIR / ".manifest.json"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}


def file_hash(path: Path) -> str:
    """SHA256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(name: str) -> str:
    """Convert a filename stem to a markdown-safe slug.

    Preserves existing naming conventions in the corpus (hyphens, underscores)
    while cleaning up spaces and special characters.
    """
    stem = Path(name).stem
    # Replace spaces with underscores (matches existing DOCX/XLSX convention)
    slug = stem.replace(" ", "_")
    # Remove characters that aren't alphanumeric, hyphens, or underscores
    slug = re.sub(r"[^\w\-]", "_", slug)
    # Collapse consecutive underscores
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_")


def load_manifest() -> dict:
    """Load the conversion manifest."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    """Save the conversion manifest."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def find_existing_markdown(source_name: str) -> Path | None:
    """Find an existing markdown file that corresponds to a source document.

    Handles the fact that existing files may use slightly different naming
    (e.g., spaces vs underscores, truncation).
    """
    stem = Path(source_name).stem
    slug = slugify(source_name)

    # Try exact slug match first
    candidate = CORPUS_DIR / f"{slug}.md"
    if candidate.exists():
        return candidate

    # Try with the original stem (hyphenated names)
    candidate = CORPUS_DIR / f"{stem}.md"
    if candidate.exists():
        return candidate

    # Normalized match: collapse underscores/hyphens and compare.
    # Also handles truncated filenames (one is a prefix of the other).
    def normalize(s: str) -> str:
        return re.sub(r"[\-_]+", "_", s).lower()

    norm_slug = normalize(slug)
    for md_file in CORPUS_DIR.glob("*.md"):
        norm_existing = normalize(md_file.stem)
        if norm_existing == norm_slug:
            return md_file
        # Handle truncated names (existing file may be shorter)
        shorter, longer = sorted([norm_existing, norm_slug], key=len)
        if len(shorter) >= 20 and longer.startswith(shorter):
            return md_file

    return None


def convert_file(source: Path) -> str:
    """Convert a source document to markdown text."""
    md = MarkItDown()
    result = md.convert(str(source))
    if not result or not result.text_content or not result.text_content.strip():
        raise ValueError(f"No content extracted from {source.name}")
    return result.text_content


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def split_large_document(
    md_path: Path, corpus_dir: Path, max_words: int = 2000
) -> list[str]:
    """Split a large markdown file into smaller topical files by H2 headings.

    If the document has no H2 headings, it is not split.

    Args:
        md_path: Path to the markdown file to potentially split.
        corpus_dir: Directory where split files will be written.
        max_words: Word count threshold. Only split if document exceeds this.

    Returns:
        List of created filenames (empty list if not split).
        If split, the original file is deleted and replaced with split files.
    """
    content = md_path.read_text()
    total_words = word_count(content)

    if total_words <= max_words:
        return []

    # Find all H2 headings
    h2_pattern = r'^## (.+)$'
    h2_matches = list(re.finditer(h2_pattern, content, re.MULTILINE))

    if not h2_matches:
        # No H2 headings found, cannot split
        return []

    # Split content by H2 boundaries
    sections = []
    for i, match in enumerate(h2_matches):
        section_title = match.group(1)
        section_start = match.start()
        section_end = (
            h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(content)
        )
        section_content = content[section_start:section_end].rstrip()
        sections.append((section_title, section_content))

    # Prepend any content before the first H2 to all sections (intro/preamble)
    preamble_end = h2_matches[0].start()
    preamble = content[:preamble_end].rstrip()

    # Generate filenames and write split files
    base_slug = md_path.stem
    created_files = []

    for section_title, section_content in sections:
        # Slugify the section title
        section_slug = slugify(section_title)
        split_filename = f"{base_slug}-{section_slug}.md"
        split_path = corpus_dir / split_filename

        # Combine preamble + section content
        split_content = preamble + "\n\n" + section_content
        split_path.write_text(split_content + "\n")
        created_files.append(split_filename)

    # Delete the original monolithic file
    md_path.unlink()

    return created_files


def main() -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    converted = []
    skipped = []
    failed = []
    bootstrapped = []
    split_docs = []

    # Collect all supported source files
    sources = sorted(
        p
        for p in DOCUMENTS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for source in sources:
        current_hash = file_hash(source)
        manifest_key = source.name

        # Check manifest
        if manifest_key in manifest:
            if manifest[manifest_key]["hash"] == current_hash:
                # Handle both string (single file) and list (split files) formats
                md_refs = manifest[manifest_key]["markdown"]
                md_files = [md_refs] if isinstance(md_refs, str) else md_refs
                if all((CORPUS_DIR / f).exists() for f in md_files):
                    skipped.append(source.name)
                    continue
            # Hash changed — re-convert below
        else:
            # Not in manifest. If markdown already exists, bootstrap the entry.
            existing = find_existing_markdown(source.name)
            if existing:
                manifest[manifest_key] = {
                    "hash": current_hash,
                    "markdown": existing.name,
                }
                bootstrapped.append(source.name)
                continue

        # Convert
        md_name = slugify(source.name) + ".md"
        md_path = CORPUS_DIR / md_name
        print(f"Converting: {source.name} -> {md_name}")

        try:
            content = convert_file(source)
            md_path.write_text(content)

            # Check if document needs splitting
            split_files = split_large_document(md_path, CORPUS_DIR, max_words=2000)

            if split_files:
                # Document was split; update manifest with split files
                print(f"  Split into {len(split_files)} files:")
                for split_file in split_files:
                    print(f"    - {split_file}")
                manifest[manifest_key] = {
                    "hash": current_hash,
                    "markdown": split_files,  # Array of filenames
                }
                split_docs.append((source.name, split_files))
            else:
                # Not split; standard single-file entry
                manifest[manifest_key] = {
                    "hash": current_hash,
                    "markdown": md_name,
                }

            converted.append(source.name)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            failed.append(source.name)

    save_manifest(manifest)

    # Report
    print(f"\nResults: {len(converted)} converted, {len(skipped)} unchanged, "
          f"{len(bootstrapped)} bootstrapped, {len(failed)} failed")
    if converted:
        print("Converted:")
        for name in converted:
            print(f"  + {name}")
    if split_docs:
        print("Documents split:")
        for source_name, split_files in split_docs:
            print(f"  ✂ {source_name} → {len(split_files)} files")
    if bootstrapped:
        print("Bootstrapped (existing markdown preserved):")
        for name in bootstrapped:
            print(f"  = {name}")
    if failed:
        print("Failed:", file=sys.stderr)
        for name in failed:
            print(f"  ! {name}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
