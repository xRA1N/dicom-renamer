#!/usr/bin/env python3
"""
DICOM Directory Renamer
Cross-platform tool to rename DICOM directories by patient name and study date.

Each directory containing DICOM files is renamed to YYYYMMDD_HHMMSS_PatientName,
moved into a year directory (YYYY, derived from StudyDate) under the root
directory, and its leftover ancestor chain is marked with a _TO_DELETE suffix.

Usage:
  python dicom_renamer.py <directory> [options]

Examples:
  python dicom_renamer.py /path/to/CT/scans
  python dicom_renamer.py /path/to/CT/scans --dry-run
  python dicom_renamer.py /path/to/CT/scans --flatten --recursive

"""

import argparse
import os
import re
import shutil
import sys


try:
    import pydicom
except ImportError:
    print("Error: pydicom is required. Install with: pip install pydicom")
    sys.exit(1)


VERSION = "1.1.0"

# Suffix appended to leftover ancestor directories after their data has been
# archived into a year directory. ASCII-only for cross-filesystem safety.
DELETE_MARKER = "_TO_DELETE"


def clean_patient_name(name):
    """Clean DICOM PatientName field.
    - Strip whitespace
    - Replace ^ (DICOM PN separator) with _
    - Collapse multiple underscores
    - Strip trailing/leading underscores
    """
    name = name.strip().replace(" ", "")
    name = name.replace("^", "_")
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name


def is_standardized(name):
    """Check if directory name already follows YYYYMMDD_HHMMSS_Name format."""
    return bool(re.match(r"^\d{8}_\d{6}_.+", name))


def get_dicom_metadata(dcm_path):
    """Read StudyDate, StudyTime, PatientName from a DICOM file."""
    try:
        ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
        patient_name = clean_patient_name(str(ds.get("PatientName", "")).strip())
        study_date = str(ds.get("StudyDate", "")).strip()
        study_time = str(ds.get("StudyTime", "")).strip()[:6]
        return study_date, study_time, patient_name
    except Exception as e:
        return None, None, None


def find_dicom_directories(root_dir, recursive=True):
    """Find all directories containing DICOM files.

    Returns list of (dir_path, dcm_files) tuples.
    """
    results = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dcm_files = [f for f in filenames if f.lower().endswith(".dcm")]
        if dcm_files:
            results.append((dirpath, sorted(dcm_files)))
        if not recursive:
            break
    return results


def flatten_dicom_files(target_dir, dry_run=False):
    """Move DICOM files from nested subdirectories up to target directory.

    Returns (moved, deleted_dirs) counts.
    """
    moved = 0
    deleted_dirs = 0

    # Find all .dcm files in subdirectories (not at the top level)
    top_dcm = set(os.listdir(target_dir))
    top_dcm = {f for f in top_dcm if f.lower().endswith(".dcm")}

    for root, dirs, files in os.walk(target_dir, topdown=False):
        if root == target_dir:
            continue

        # Get DICOM files in this subdirectory
        dcm_files = [f for f in files if f.lower().endswith(".dcm")]
        if not dcm_files:
            continue

        for f in dcm_files:
            src = os.path.join(root, f)
            dst = os.path.join(target_dir, f)
            if src == dst:
                continue
            if os.path.exists(dst):
                continue
            if not dry_run:
                shutil.move(src, dst)
            moved += 1

        # Remove empty subdirectories
        remaining = [x for x in os.listdir(root) if x != ".DS_Store"]
        if not remaining:
            if not dry_run:
                try:
                    os.rmdir(root)
                    deleted_dirs += 1
                except OSError:
                    pass
            else:
                deleted_dirs += 1

    if moved > 0:
        # Re-check parent directory for now-empty deeper dirs
        for root, dirs, files in os.walk(target_dir, topdown=False):
            if root == target_dir:
                continue
            remaining = [x for x in os.listdir(root) if x != ".DS_Store"]
            if not remaining:
                if not dry_run:
                    try:
                        os.rmdir(root)
                        deleted_dirs += 1
                    except OSError:
                        pass
                else:
                    deleted_dirs += 1

    return moved, deleted_dirs


def move_directory(old_path, new_name, dest_parent, dry_run=False):
    """Move a directory into dest_parent under new_name.

    Handles naming conflicts by appending _2, _3, etc.
    Returns the final name used, or None on failure.
    """
    new_path = os.path.join(dest_parent, new_name)

    if os.path.exists(new_path):
        base = new_name
        suffix = 2
        while os.path.exists(os.path.join(dest_parent, f"{base}_{suffix}")):
            suffix += 1
            if suffix > 100:
                return None
        new_name = f"{base}_{suffix}"

    if not dry_run:
        shutil.move(old_path, os.path.join(dest_parent, new_name))

    return new_name


def remove_empty_subdirs(target_dir, dry_run=False):
    """Remove empty subdirectories inside target_dir (bottom-up).

    Returns count of removed (or removable) directories.
    """
    removed = 0
    for root, dirs, files in os.walk(target_dir, topdown=False):
        if root == target_dir:
            continue
        remaining = [x for x in os.listdir(root) if x != ".DS_Store"]
        if not remaining:
            if not dry_run:
                try:
                    os.rmdir(root)
                    removed += 1
                except OSError:
                    pass
            else:
                removed += 1
    return removed


def mark_for_deletion(dir_path, dry_run=False):
    """Append DELETE_MARKER to a directory name. Returns True if marked."""
    name = os.path.basename(dir_path)
    if name.endswith(DELETE_MARKER):
        return False
    if not os.path.isdir(dir_path):
        return False
    parent = os.path.dirname(dir_path)
    new_path = os.path.join(parent, name + DELETE_MARKER)
    if not dry_run:
        try:
            os.rename(dir_path, new_path)
        except OSError:
            return False
    return True


def mark_ancestors(src_dir, root_dir, protected, dry_run=False, seen=None):
    """Mark the ancestor chain of src_dir with DELETE_MARKER.

    Walks from the direct parent up to root_dir (exclusive). Stops when the
    candidate directory is itself protected or still contains a protected
    directory beneath it (unarchived data would be caught in the marking).
    Skips missing or already-marked directories. `seen` collects every dir
    handled so far, keeping dry-run previews free of duplicates.

    Returns list of newly marked paths.
    """
    marked = []
    current = os.path.dirname(os.path.abspath(src_dir))
    while current.startswith(root_dir.rstrip(os.sep) + os.sep):
        blocked = current in protected or any(
            p.startswith(current + os.sep) for p in protected
        )
        if blocked:
            break
        if seen is None or current not in seen:
            if mark_for_deletion(current, dry_run=dry_run):
                marked.append(current)
            if seen is not None:
                seen.add(current)
        current = os.path.dirname(current)
    return marked


def process_directory(
    root_dir,
    dry_run=False,
    flatten=False,
    recursive=True,
    quiet=False,
):
    """Main processing function.

    Phase 1: rename each DICOM directory and move it into root/YYYY/.
    Phase 2: mark leftover ancestor chains with DELETE_MARKER.

    Returns summary stats.
    """
    stats = {
        "scanned": 0,
        "archived": 0,
        "skipped_standardized": 0,
        "skipped_no_dicom": 0,
        "flattened_moved": 0,
        "flattened_deleted": 0,
        "cleaned_dirs": 0,
        "conflicts": 0,
        "year_dirs_created": 0,
        "marked_dirs": 0,
        "errors": [],
    }

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory", file=sys.stderr)
        return stats

    root_dir = os.path.abspath(root_dir)

    # Find all directories with DICOM files
    dirs = find_dicom_directories(root_dir, recursive=recursive)
    stats["scanned"] = len(dirs)

    if not dirs:
        if not quiet:
            print(f"No DICOM files found in {root_dir}")
        return stats

    # Deepest first, so nested data directories are archived before parents
    dirs.sort(key=lambda item: item[0].count(os.sep), reverse=True)

    ensured_years = set()
    moved_sources = []

    # ---- Phase 1: rename and archive into year directories ----
    for dir_path, dcm_files in dirs:
        dir_name = os.path.basename(dir_path)
        rel_path = os.path.relpath(dir_path, root_dir)
        standardized = is_standardized(dir_name)

        if standardized:
            date = dir_name[:8]
            time_val = dir_name[9:15]
            patient_name = dir_name.split("_", 2)[2]
            new_name = dir_name
        else:
            dcm_path = os.path.join(dir_path, dcm_files[0])
            date, time_val, patient_name = get_dicom_metadata(dcm_path)

            if not date or not time_val or not patient_name:
                stats["skipped_no_dicom"] += 1
                if not quiet:
                    print(f"  [SKIP] {rel_path} — could not read DICOM metadata")
                continue

            new_name = f"{date}_{time_val}_{patient_name}"

        year = date[:4] if re.match(r"^\d{4}", str(date)) else None
        if not year:
            stats["skipped_no_dicom"] += 1
            stats["errors"].append(f"{rel_path}: invalid study date '{date}'")
            continue

        year_dir = os.path.join(root_dir, year)

        # Already organized: correct name inside its own year directory
        if (
            os.path.dirname(os.path.abspath(dir_path)) == year_dir
            and dir_name == new_name
        ):
            stats["skipped_standardized"] += 1
            if not quiet:
                print(f"  [SKIP] {rel_path} — already organized")
            continue

        # Optionally flatten nested DICOM files first
        if flatten:
            top_dcms = [f for f in os.listdir(dir_path) if f.lower().endswith(".dcm")]
            if not top_dcms:
                moved, deleted = flatten_dicom_files(dir_path, dry_run=dry_run)
                stats["flattened_moved"] += moved
                stats["flattened_deleted"] += deleted
                if moved > 0 and not quiet:
                    print(f"  [FLAT] {rel_path} — moved {moved} DICOMs up, "
                          f"deleted {deleted} empty dirs")

        # Drop now-empty subdirectories so they do not travel into the archive
        cleaned = remove_empty_subdirs(dir_path, dry_run=dry_run)
        stats["cleaned_dirs"] += cleaned

        # Create the year directory once
        if year not in ensured_years and not os.path.isdir(year_dir):
            if not dry_run:
                try:
                    os.makedirs(year_dir)
                except OSError as e:
                    stats["errors"].append(f"{rel_path}: cannot create {year}: {e}")
                    continue
            if not quiet:
                print(f"  [DIR]  created year directory {year}/")
            stats["year_dirs_created"] += 1
        ensured_years.add(year)

        # Move into the year directory
        result = move_directory(dir_path, new_name, year_dir, dry_run=dry_run)
        if result is None:
            stats["errors"].append(f"{rel_path}: move failed")
            if not quiet:
                print(f"  [ERR]  {rel_path} → move failed")
            continue

        is_conflict = result != new_name
        if is_conflict:
            stats["conflicts"] += 1

        stats["archived"] += 1
        moved_sources.append(dir_path)
        if not quiet:
            conflict_msg = f" (conflict, renamed as {result})" if is_conflict else ""
            print(f"  [OK]   {rel_path} → {year}/{result}{conflict_msg}")

    # ---- Phase 2: mark leftover ancestor chains for deletion ----
    protected = {os.path.abspath(p) for p, _ in dirs} - {
        os.path.abspath(p) for p in moved_sources
    }

    seen = set()
    for src in moved_sources:
        marked = mark_ancestors(
            src, root_dir, protected, dry_run=dry_run, seen=seen
        )
        stats["marked_dirs"] += len(marked)
        for m in marked:
            if not quiet:
                print(f"  [MARK] {os.path.relpath(m, root_dir)}{DELETE_MARKER}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="DICOM Directory Renamer v" + VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/scans --dry-run
  %(prog)s /path/to/scans --flatten --recursive
  %(prog)s /path/to/scans --recursive --quiet

Each DICOM directory is renamed to YYYYMMDD_HHMMSS_PatientName, moved into a
year directory (YYYY) under the root, and its leftover ancestors are suffixed
with {marker} for manual review before deletion.
""".format(marker=DELETE_MARKER),
    )

    parser.add_argument(
        "directory",
        help="Root directory containing DICOM subdirectories to process",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview changes without modifying anything",
    )
    parser.add_argument(
        "--flatten",
        "-f",
        action="store_true",
        help="Move DICOM files from nested subdirectories up to parent before renaming",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=True,
        help="Search recursively for DICOM directories (default: True)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only scan the top-level directory, do not recurse",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress detailed output, show summary only",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    args = parser.parse_args()

    # Handle --no-recursive override
    recursive = not args.no_recursive

    if args.dry_run:
        print("DRY RUN — no changes will be made\n")

    if not args.quiet:
        print(f"Scanning: {args.directory}")
        print(f"  Archive: renamed dirs will be moved to <root>/<year>/"
              f", ancestors marked {DELETE_MARKER}")
        if args.flatten:
            print("  Flatten: enabled (DICOMs will be moved from subdirectories)")
        print()

    stats = process_directory(
        root_dir=args.directory,
        dry_run=args.dry_run,
        flatten=args.flatten,
        recursive=recursive,
        quiet=args.quiet,
    )

    # Summary
    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Directories scanned:       {stats['scanned']}")
    print(f"  Archived to year dirs:     {stats['archived']}")
    print(f"  Conflicts (auto-resolved): {stats['conflicts']}")
    print(f"  Skipped (organized):       {stats['skipped_standardized']}")
    print(f"  Skipped (no metadata):     {stats['skipped_no_dicom']}")
    if stats["year_dirs_created"]:
        print(f"  Year dirs created:         {stats['year_dirs_created']}")
    empty_total = stats["cleaned_dirs"] + stats["flattened_deleted"]
    if empty_total:
        print(f"  Empty dirs removed:        {empty_total}")
    print(f"  Ancestors marked {DELETE_MARKER}: {stats['marked_dirs']}")
    if stats["errors"]:
        print(f"  Errors:                  {len(stats['errors'])}")
        for e in stats["errors"][:5]:
            print(f"    - {e}")
    print()

    if args.dry_run:
        print("DRY RUN — no changes were made")

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
