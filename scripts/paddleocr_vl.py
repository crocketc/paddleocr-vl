# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 文档识别脚本
支持 PDF/PNG/JPG/BMP/TIF 等格式的 OCR 识别
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

import requests

from config_loader import (
    load_config,
    load_mode_config,
    get_api_config,
    get_output_config,
    get_mode_output_format,
    get_token_from_config,
    DEFAULT_ENV_PATH,
)

# 支持的图片格式
IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
# 支持的文档格式
DOCUMENT_FORMATS = {".pdf"}


def encode_image_to_base64(image_path: str) -> str:
    """将图片文件编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_pdf_to_base64(pdf_path: str) -> str:
    """将 PDF 文件编码为 base64"""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_ocr_api(
    file_path: str,
    token: str,
    api_config: Dict[str, Any],
    ocr_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    调用 PaddleOCR-VL API 进行文档识别
    AI Studio 版本使用 Authorization header

    Args:
        file_path: 文件路径
        token: API Token
        api_config: API 配置（base_url, timeout, max_retries）
        ocr_config: OCR 参数配置

    Returns:
        API 响应结果
    """
    base_url = api_config.get("base_url", "https://l3s4h7i4v7keefk4.aistudio-app.com/layout-parsing")
    timeout = api_config.get("timeout", 300)
    max_retries = api_config.get("max_retries", 3)

    file_ext = Path(file_path).suffix.lower()

    # 编码文件
    if file_ext == ".pdf":
        file_data = encode_pdf_to_base64(file_path)
        file_type = 0  # PDF
    else:
        file_data = encode_image_to_base64(file_path)
        file_type = 1  # 图片

    # 构建请求体（AI Studio 格式）
    payload = {
        "file": file_data,
        "fileType": file_type,
    }

    # 添加 OCR 配置参数（过滤值为 None 的参数）
    if ocr_config:
        for key, value in ocr_config.items():
            if value is not None:
                payload[key] = value

    # 构建请求头
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }

    # 发送请求，支持重试
    for attempt in range(max_retries):
        try:
            print(f"正在识别: {file_path} (尝试 {attempt + 1}/{max_retries})")
            response = requests.post(base_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if "error_code" in result:
                raise Exception(f"API 错误: {result.get('error_msg', '未知错误')}")

            return result

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"请求超时，{wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                raise Exception(f"请求超时: {file_path}")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"请求失败: {e}，{wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                raise Exception(f"请求失败: {e}")
        except Exception as e:
            raise Exception(f"识别失败: {e}")


def save_markdown_result(
    result: Dict[str, Any],
    output_dir: str,
    base_name: str,
):
    """
    保存 Markdown 结果
    支持 AI Studio 格式：result["layoutParsingResults"]

    Args:
        result: API 响应结果
        output_dir: 输出目录
        base_name: 文件基础名
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # AI Studio 格式
    if "layoutParsingResults" in result.get("result", {}):
        layout_results = result["result"]["layoutParsingResults"]
        for i, res in enumerate(layout_results):
            md_filename = output_path / f"{base_name}_{i}.md"
            markdown_text = res.get("markdown", {}).get("text", "")
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            print(f"Markdown 结果已保存: {md_filename}")
    # 原格式兼容
    else:
        markdown_content = result.get("result", {}).get("markdown", "")
        if not markdown_content:
            print("警告: 未获取到 Markdown 内容")
            return
        output_file = output_path / f"{base_name}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Markdown 结果已保存: {output_file}")


def save_json_result(
    result: Dict[str, Any],
    json_file: str,
):
    """
    保存 JSON 结果

    Args:
        result: API 响应结果
        json_file: JSON 输出文件路径
    """
    output_path = Path(json_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"JSON 结果已保存: {output_path}")


def ocr_file(
    file_path: str,
    mode: str = "标准",
    output_dir: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    对单个文件进行 OCR 识别
    Token 从配置文件中的 .env 自动读取

    Args:
        file_path: 文件路径
        mode: 预设模式（快速/标准/精细）
        output_dir: 输出目录
        config_path: 配置文件路径

    Returns:
        API 响应结果
    """
    # 加载配置（自动合并 .env 文件）
    config = load_config(config_path)
    api_config = get_api_config(config)
    output_config = get_output_config(config)
    ocr_config = load_mode_config(mode, config_path)

    # 从配置中获取 Token
    token = get_token_from_config(config)
    if not token:
        raise ValueError(f"Token 未设置，请在 {DEFAULT_ENV_PATH} 文件中配置 PADDLEOCR_TOKEN")

    # 获取模式的输出格式
    output_format = get_mode_output_format(ocr_config)

    # 设置默认输出目录
    if output_dir is None:
        output_dir = output_config.get("markdown_dir", "output")

    # 调用 API
    result = call_ocr_api(file_path, token, api_config, ocr_config)

    # 保存结果（使用模式配置的输出格式）
    base_name = Path(file_path).stem

    if output_format in ["markdown", "both"]:
        save_markdown_result(result, output_dir, base_name)

    if output_format in ["json", "both"]:
        json_file = os.path.join(output_dir, f"{base_name}.json")
        save_json_result(result, json_file)

    return result


def batch_ocr(
    files: List[str],
    mode: str = "标准",
    output_dir: Optional[str] = None,
    config_path: Optional[Path] = None,
):
    """
    批量处理多个文件
    Token 从配置文件中的 .env 自动读取

    Args:
        files: 文件路径列表
        mode: 预设模式
        output_dir: 输出目录
        config_path: 配置文件路径
    """
    success_count = 0
    failed_files = []

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理文件: {file_path}")
        try:
            ocr_file(file_path, mode, output_dir, config_path)
            success_count += 1
        except Exception as e:
            print(f"错误: {e}")
            failed_files.append((file_path, str(e)))

    # 输出摘要
    print(f"\n{'='*50}")
    print(f"处理完成: 成功 {success_count}/{len(files)}")

    if failed_files:
        print(f"\n失败文件列表:")
        for file_path, error in failed_files:
            print(f"  - {file_path}: {error}")


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PaddleOCR-VL 文档识别工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
预设模式说明:
  快速  - 适合简单文档，处理速度快（禁用大部分高级功能）
  标准  - 平衡速度与精度，适合大多数场景（推荐）
  精细  - 最高精度，适合复杂文档（启用所有高级功能）

配置说明:
  Token 配置位置：scripts/.env 文件中的 PADDLEOCR_TOKEN
  Token 获取地址：https://aistudio.baidu.com/account/accessToken

示例:
  # 使用标准模式识别单个文件
  python paddleocr_vl.py document.pdf

  # 使用快速模式识别
  python paddleocr_vl.py document.pdf --mode 快速

  # 使用精细模式
  python paddleocr_vl.py document.pdf --mode 精细

  # 批量处理多个文件
  python paddleocr_vl.py file1.pdf file2.jpg --mode 标准

  # 指定输出目录
  python paddleocr_vl.py document.pdf --output ./output
        """
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="要识别的文件路径（支持 PDF/PNG/JPG/BMP/TIF）"
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["快速", "标准", "精细"],
        default="标准",
        help="预设模式（默认: 标准）"
    )

    parser.add_argument(
        "--output", "-o",
        help="输出目录（默认: 配置文件中的 markdown_dir）"
    )

    parser.add_argument(
        "--config", "-c",
        help="配置文件路径（默认: scripts/config.yaml）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    # 检查 .env 文件是否存在
    if not DEFAULT_ENV_PATH.exists():
        print(f"错误: 配置文件不存在: {DEFAULT_ENV_PATH}")
        print(f"请创建 .env 文件并配置 PADDLEOCR_TOKEN")
        print(f"Token 获取地址: https://aistudio.baidu.com/account/accessToken")
        sys.exit(1)

    # 检查文件是否存在
    files = []
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"警告: 文件不存在: {file_path}")
        elif path.suffix.lower() not in IMAGE_FORMATS | DOCUMENT_FORMATS:
            print(f"警告: 不支持的文件格式: {file_path}")
        else:
            files.append(str(path))

    if not files:
        print("错误: 没有有效的文件可处理")
        sys.exit(1)

    # 处理文件
    config_path = Path(args.config) if args.config else None

    if len(files) == 1:
        ocr_file(files[0], args.mode, args.output, config_path)
    else:
        batch_ocr(files, args.mode, args.output, config_path)


if __name__ == "__main__":
    main()
