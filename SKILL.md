---
name: paddleocr-vl
description: 基于百度飞桨 PaddleOCR-VL-1.5 的文档识别技能。当用户需要对 PDF、PNG、JPG、BMP、TIF 等格式的文档进行 OCR 文字识别时使用此技能。支持文字、表格、公式、图表识别，输出 Markdown 格式结果。
---

# PaddleOCR-VL

## 功能特点

- **多格式支持**：PDF、PNG、JPG、JPEG、BMP、TIF、TIFF
- **智能识别**：支持文字、表格、公式、图表识别
- **版面分析**：自动检测文档版面，智能排序
- **多种模式**：快速、标准、精细三种预设模式
- **中文配置**：友好的中文配置文件

## 安装依赖

```bash
pip install pyyaml requests
```

## 配置 Token

### 在 .env 文件中配置（推荐）

编辑 `scripts/.env` 文件，设置 API Token：

```bash
# Token 获取地址：https://aistudio.baidu.com/account/accessToken
PADDLEOCR_TOKEN=your_api_token_here
```

如需创建 .env 文件，可复制模板：

```bash
cp scripts/.env.example scripts/.env
```

## 使用方法

### 命令行使用

```bash
# 使用标准模式识别单个文件（默认）
python scripts/paddleocr_vl.py document.pdf

# 使用快速模式
python scripts/paddleocr_vl.py document.pdf --mode 快速

# 使用精细模式
python scripts/paddleocr_vl.py document.pdf --mode 精细

# 批量处理多个文件
python scripts/paddleocr_vl.py file1.pdf file2.jpg --mode 标准

# 指定输出目录
python scripts/paddleocr_vl.py document.pdf --output ./output
```

### Python 代码使用

```python
from scripts.paddleocr_vl import ocr_file

# 使用预设模式（Token 从 .env 文件自动读取）
result = ocr_file(
    file_path="document.pdf",
    mode="标准"
)

# 查看结果
markdown_text = result["result"]["markdown"]
print(markdown_text)
```

## 预设模式说明

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| **快速** | 处理速度最快 | 简单文档、纯文本 |
| **标准** | 平衡速度与精度 | 大多数场景（推荐） |
| **精细** | 最高精度 | 复杂文档、包含表格/图表/公式 |

## 参数配置

通过修改 `scripts/config.yaml` 的 `options` 部分可自定义参数：

```yaml
options:
  # 文档矫正
  use_doc_orientation_classify: true  # 方向矫正
  use_doc_unwarping: true             # 扭曲矫正

  # 版面检测
  use_layout_detection: true          # 版面检测
  layout_threshold: 0.5               # 检测阈值

  # 内容识别
  use_chart_recognition: true         # 图表识别

  # 输出格式
  prettify_markdown: true             # Markdown 美化
  show_formula_number: true           # 显示公式编号
```

详细参数说明请参考 [references/config-guide.md](references/config-guide.md)。

## 输出结果

识别结果默认保存为 Markdown 文件：

```
output/
└── document.md
```

可在 `config.yaml` 中配置输出格式（markdown/json/both）。

## 目录结构

```
.
├── scripts/
│   ├── config.yaml          # 配置文件
│   ├── config_loader.py     # 配置加载器（支持动态读取 .env）
│   ├── paddleocr_vl.py      # 主脚本
│   ├── .env                 # 环境变量配置（需自行创建）
│   └── .env.example         # 环境变量模板
├── references/
│   └── config-guide.md      # 详细配置指南
└── SKILL.md                 # 本文件
```

## 常见问题

**Q: 识别结果不准确怎么办？**
A: 尝试使用"精细"模式，或在配置文件中调整相关参数。

**Q: 如何处理跨页表格？**
A: 使用"精细"模式，会自动启用 `merge_tables` 功能合并跨页表格。

**Q: 支持哪些文件格式？**
A: 支持 PDF、PNG、JPG、JPEG、BMP、TIF、TIFF 格式。
