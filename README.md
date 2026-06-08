# DICOM Directory Renamer

Cross-platform tool to rename DICOM directories by patient name and study date.

跨平台工具，可根据患者姓名和检查日期重命名 DICOM 目录。

## Features / 功能特性

- Renames directories containing DICOM files to `YYYYMMDD_HHMMSS_PatientName` format
- Handles DICOM PatientName field (converts `^` separators to `_`)
- Auto-resolves naming conflicts by appending `_2`, `_3`, etc.
- Optionally flattens nested DICOM files from subdirectories
- Dry-run mode for previewing changes
- Recursive directory scanning
- Works on Windows, Linux, and macOS

- 将包含 DICOM 文件的目录重命名为 `YYYYMMDD_HHMMSS_患者姓名` 格式
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
├── 张三/
├── patient_data/
└── 李四/
```

After / 之后:
```
scans/
├── 20240115_093021_张三/
├── 20240220_143512_王五/
└── 20240310_112008_李四/
```

## Cross-Platform Notes / 跨平台说明

- **Windows**: Run with `python dicom_renamer.py` from Command Prompt or PowerShell
- **Linux/macOS**: Run with `python3 dicom_renamer.py` or make executable with `chmod +x dicom_renamer.py`
- Network drives are supported on all platforms

- **Windows**: 在命令提示符或 PowerShell 中运行 `python dicom_renamer.py`
- **Linux/macOS**: 使用 `python3 dicom_renamer.py` 运行，或使用 `chmod +x dicom_renamer.py` 添加执行权限
- 所有平台均支持网络驱动器

## License / 许可证

MIT