# DICOM Directory Renamer

Cross-platform tool to rename DICOM directories by patient name and study date.

## Features

- Renames directories containing DICOM files to `YYYYMMDD_HHMMSS_PatientName` format
- Handles DICOM PatientName field (converts `^` separators to `_`)
- Auto-resolves naming conflicts by appending `_2`, `_3`, etc.
- Optionally flattens nested DICOM files from subdirectories
- Dry-run mode for previewing changes
- Recursive directory scanning
- Works on Windows, Linux, and macOS

## Requirements

- Python 3.8+
- `pydicom` library

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install pydicom directly
pip install pydicom
```

## Usage

```bash
# Preview changes (dry run)
python dicom_renamer.py /path/to/scans --dry-run

# Rename directories
python dicom_renamer.py /path/to/scans

# Flatten nested DICOMs and rename
python dicom_renamer.py /path/to/scans --flatten

# Quiet mode (summary only)
python dicom_renamer.py /path/to/scans --quiet

# Help
python dicom_renamer.py --help
```

## Directory Naming Convention

Before:
```
scans/
├── 张三/
├── patient_data/
└── 李四/
```

After:
```
scans/
├── 20240115_093021_张三/
├── 20240220_143512_王五/
└── 20240310_112008_李四/
```

## Cross-Platform Notes

- **Windows**: Run with `python dicom_renamer.py` from Command Prompt or PowerShell
- **Linux/macOS**: Run with `python3 dicom_renamer.py` or make executable with `chmod +x dicom_renamer.py`
- Network drives are supported on all platforms

## License

MIT
