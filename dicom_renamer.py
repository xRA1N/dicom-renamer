#!/usr/bin/env python3
"""
DICOM Directory Renamer
Cross-platform tool to rename DICOM directories by patient name and study date.

Usage:
  python dicom_renamer.py <directory> [options]

Examples:
  python dicom_renamer.py /path/to/CT/scans
  python dicom_renamer.py /path/to/CT/scans --dry-run
  python dicom_renamer.py /path/to/CT/scans --flatten --recursive

"""

import argparse
import glob
import os
import re
import shutil
import sys


try:
    import pydicom
except ImportError:
    print("Error: pydicom is required. Install with: pip install pydicom")
    sys.exit(1)


VERSION = "1.0.0"


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


def rename_directory(old_path, new_name, dry_run=False):
    """Rename a directory to new_name in the same parent."""
    parent = os.path.dirname(old_path)
    new_path = os.path.join(parent, new_name)

    if os.path.exists(new_path):
        # Handle conflict by appending _2, _3, etc.
        base = new_name
        suffix = 2
        while os.path.exists(os.path.join(parent, f"{base}_{suffix}")):
            suffix += 1
            if suffix > 100:
                return None
        new_name = f"{base}_{suffix}"
        new_path = os.path.join(parent, new_name)

    if not dry_run:
        os.rename(old_path, new_path)

    return new_name


def process_directory(
    root_dir,
    dry_run=False,
    flatten=False,
    recursive=True,
    quiet=False,
):
    """Main processing function.

    Returns summary stats.
    """
    stats = {
        "scanned": 0,
        "renamed": 0,
        "skipped_standardized": 0,
        "skipped_no_dicom": 0,
        "flattened_moved": 0,
        "flattened_deleted": 0,
        "conflicts": 0,
        "errors": [],
    }

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory", file=sys.stderr)
        return stats

    # Find all directories with DICOM files
    dirs = find_dicom_directories(root_dir, recursive=recursive)
    stats["scanned"] = len(dirs)

    if not dirs:
        if not quiet:
            print(f"No DICOM files found in {root_dir}")
        return stats

    # Process each directory
    for dir_path, dcm_files in dirs:
        dir_name = os.path.basename(dir_path)

        # Skip already standardized
        if is_standardized(dir_name):
            stats["skipped_standardized"] += 1
            if not quiet:
                print(f"  [SKIP] {dir_name} — already standardized")
            continue

        # Optionally flatten nested DICOM files first
        if flatten:
            # Check if DICOMs are in subdirectories
            top_dcms = [f for f in os.listdir(dir_path) if f.lower().endswith(".dcm")]
            if not top_dcms:
                moved, deleted = flatten_dicom_files(dir_path, dry_run=dry_run)
                stats["flattened_moved"] += moved
                stats["flattened_deleted"] += deleted
                if moved > 0 and not quiet:
                    print(f"  [FLAT] {dir_name} — moved {moved} DICOMs up, "
                          f"deleted {deleted} empty dirs")

        # Read DICOM metadata
        dcm_path = os.path.join(dir_path, dcm_files[0])
        date, time_val, patient_name = get_dicom_metadata(dcm_path)

        if not date or not time_val or not patient_name:
            stats["skipped_no_dicom"] += 1
            if not quiet:
                print(f"  [SKIP] {dir_name} — could not read DICOM metadata")
            continue

        new_name = f"{date}_{time_val}_{patient_name}"

        if dir_name == new_name:
            stats["skipped_standardized"] += 1
            if not quiet:
                print(f"  [SKIP] {dir_name} — already correct")
            continue

        # Rename
        result = rename_directory(dir_path, new_name, dry_run=dry_run)
        if result is None:
            stats["errors"].append(f"{dir_name}: rename failed")
            if not quiet:
                print(f"  [ERR]  {dir_name} → rename failed")
            continue

        is_conflict = result != new_name
        if is_conflict:
            stats["conflicts"] += 1

        stats["renamed"] += 1
        if not quiet:
            conflict_msg = f" (conflict, renamed as {result})" if is_conflict else ""
            print(f"  [OK]   {dir_name} → {result}{conflict_msg}")

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
        """,
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
    print(f"  Directories scanned:     {stats['scanned']}")
    print(f"  Renamed:                 {stats['renamed']}")
    print(f"  Conflicts (auto-resolved): {stats['conflicts']}")
    print(f"  Skipped (already std):   {stats['skipped_standardized']}")
    print(f"  Skipped (no metadata):   {stats['skipped_no_dicom']}")
    if args.flatten:
        print(f"  DICOM files moved up:    {stats['flattened_moved']}")
        print(f"  Empty dirs deleted:      {stats['flattened_deleted']}")
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
