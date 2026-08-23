# DICOM Directory Renamer

Cross-platform tool to rename DICOM directories by patient name and study date.

跨平台工具，可根据患者姓名和检查日期重命名 DICOM 目录。

## Features / 功能特性

- Renames directories containing DICOM files to `YYYYMMDD_HHMMSS_PatientName` format
- **Archives each renamed directory into a year folder `YYYY/` under the root** (year from StudyDate)
- **Marks leftover ancestor directories with a `_TO_DELETE` suffix for manual review**
- Handles DICOM PatientName field (converts `^` separators to `_`)
- Auto-resolves naming conflicts by appending `_2`, `_3`, etc.
- Optionally flattens nested DICOM files from subdirectories
- Dry-run mode for previewing changes
- Recursive directory scanning
- Works on Windows, Linux, and macOS

- 将包含 DICOM 文件的目录重命名为 `YYYYMMDD_HHMMSS_患者姓名` 格式
- **更名后的目录自动归档到根目录下按年份命名的 `YYYY/` 目录中**（年份取自检查日期）
- **残留的祖先目录添加 `_TO_DELETE` 后缀标记，等待人工确认后删除**
- 处理 DICOM 患者姓名字段（将 `^` 分隔符转换为 `_`）
- 自动解决命名冲突，添加 `_2`、`_3` 等后缀
- 可选择将子目录中的嵌套 DICOM 文件扁平化
- 预览模式，可查看更改效果
- 递归扫描目录
- 支持 Windows、Linux 和 macOS 系统

## Requirements / 系统要求

- Python 3.8+
- `pydicom` 库

## Installation / 安装

```bash
# Install dependencies
pip install -r requirements.txt

# Or install pydicom directly
pip install pydicom

# 安装依赖
pip install -r requirements.txt

# 或直接安装 pydicom
pip install pydicom
```

## Usage / 使用方法

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

# 预览更改（预运行模式）
python dicom_renamer.py /path/to/scans --dry-run

# 重命名目录
python dicom_renamer.py /path/to/scans

# 扁平化嵌套的 DICOM 文件并重命名
python dicom_renamer.py /path/to/scans --flatten

# 静默模式（仅显示摘要）
python dicom_renamer.py /path/to/scans --quiet

# 帮助
python dicom_renamer.py --help
```

## Directory Naming Convention / 目录命名规范

Before / 之前:
```
scans/
└── 医院数据/
    └── 3月批次/
        ├── patient_a/          (contains .dcm files)
        └── patient_b/
            └── ct/             (contains .dcm files)
```

After / 之后:
```
scans/
├── 2024/
│   └── 20240115_093021_张三/   (renamed + moved here)
├── 2025/
│   └── 20250210_153000_李四/   (renamed + moved here)
└── 医院数据_TO_DELETE/         (marked for manual review)
    └── 3月批次_TO_DELETE/
```

### Archiving & Delete Markers / 归档与删除标记

1. Each directory containing DICOM files is renamed to the standard format and
   **moved into `root/YYYY/`**, where YYYY comes from the study date. Directories
   already named in standard format are relocated as well.
2. After all data has been archived, every leftover ancestor directory is renamed
   with a **`_TO_DELETE`** suffix — nothing is deleted automatically; review and
   remove them manually.
3. Safety rules: directories whose metadata cannot be read stay in place, and any
   ancestor still containing such un-archived data is never marked.

1. 每个包含 DICOM 文件的目录都会重命名为标准格式并**移动到根目录下的 `YYYY/` 年份目录**，
   年份取自检查日期。已是标准命名的目录同样会被归位。
2. 全部数据归档完成后，残留的各级祖先目录会被重命名并加上 **`_TO_DELETE`** 后缀 ——
   工具不会自动删除任何内容，请人工确认后手动清理。
3. 安全规则：元数据读取失败的目录保持原位不动；若某祖先目录下仍残留此类未归档数据，
   则该祖先及其上层都不会被标记。

## Cross-Platform Notes / 跨平台说明

- **Windows**: Run with `python dicom_renamer.py` from Command Prompt or PowerShell
- **Linux/macOS**: Run with `python3 dicom_renamer.py` or make executable with `chmod +x dicom_renamer.py`
- Network drives are supported on all platforms

- **Windows**: 在命令提示符或 PowerShell 中运行 `python dicom_renamer.py`
- **Linux/macOS**: 使用 `python3 dicom_renamer.py` 运行，或使用 `chmod +x dicom_renamer.py` 添加执行权限
- 所有平台均支持网络驱动器

## License / 许可证

MIT