# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 配置文件加载器
支持动态读取 .env 文件中的配置
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
DEFAULT_ENV_PATH = Path(__file__).parent / ".env"


def load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """
    加载 .env 文件中的环境变量

    Args:
        env_path: .env 文件路径，默认使用 .env

    Returns:
        环境变量字典
    """
    if env_path is None:
        env_path = DEFAULT_ENV_PATH

    if not env_path.exists():
        return {}

    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue
            # 解析 KEY=VALUE 格式
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def load_config(config_path: Optional[Path] = None, env_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件，并自动合并 .env 文件中的配置

    Args:
        config_path: 配置文件路径，默认使用 config.yaml
        env_path: .env 文件路径，默认使用 .env

    Returns:
        配置字典（已合并 .env 中的环境变量）
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 加载 .env 文件并合并到配置中
    env_vars = load_env_file(env_path)

    # 合并 API 配置
    if "api" in config:
        api_config = config["api"]
        # 从 .env 读取 PADDLEOCR_TOKEN
        if "PADDLEOCR_TOKEN" in env_vars:
            api_config["token"] = env_vars["PADDLEOCR_TOKEN"]
        # 从 .env 读取 PADDLEOCR_API_URL（如果设置）
        if "PADDLEOCR_API_URL" in env_vars:
            api_config["base_url"] = env_vars["PADDLEOCR_API_URL"]
        # 从 .env 读取 PADDLEOCR_TIMEOUT（如果设置）
        if "PADDLEOCR_TIMEOUT" in env_vars:
            api_config["timeout"] = int(env_vars["PADDLEOCR_TIMEOUT"])
        # 从 .env 读取 PADDLEOCR_MAX_RETRIES（如果设置）
        if "PADDLEOCR_MAX_RETRIES" in env_vars:
            api_config["max_retries"] = int(env_vars["PADDLEOCR_MAX_RETRIES"])

    return config


def get_preset_config(config: Dict[str, Any], mode: str = "标准") -> Dict[str, Any]:
    """
    获取预设模式的配置

    Args:
        config: 完整配置字典
        mode: 预设模式名称（快速/标准/精细）

    Returns:
        预设模式配置字典
    """
    presets = config.get("presets", {})

    if mode not in presets:
        available = list(presets.keys())
        raise ValueError(f"预设模式 '{mode}' 不存在，可选: {available}")

    return presets[mode].copy()


def merge_options(base_config: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并用户自定义配置，只保留非 null 的值

    Args:
        base_config: 基础配置（预设模式配置）
        options: 用户自定义配置

    Returns:
        合并后的配置字典
    """
    result = base_config.copy()
    for key, value in options.items():
        if value is not None:
            # 转换参数名：下划线转驼峰
            camel_key = to_camel_case(key)
            result[camel_key] = value
    return result


def to_camel_case(snake_str: str) -> str:
    """
    下划线命名转驼峰命名

    Args:
        snake_str: 下划线命名的字符串

    Returns:
        驼峰命名的字符串
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def get_api_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取 API 配置

    Args:
        config: 完整配置字典

    Returns:
        API 配置字典
    """
    return config.get("api", {})


def get_mode_output_format(mode_config: Dict[str, Any]) -> str:
    """
    获取预设模式的输出格式

    Args:
        mode_config: 模式配置字典

    Returns:
        输出格式: markdown | json | both
    """
    return mode_config.get("outputFormat", "markdown")


def get_output_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取输出配置

    Args:
        config: 完整配置字典

    Returns:
        输出配置字典
    """
    return config.get("output", {})


def get_token_from_config(config: Dict[str, Any]) -> Optional[str]:
    """
    从配置中获取 Token（已从 .env 文件合并）

    Args:
        config: 完整配置字典

    Returns:
        API Token 字符串，如果未设置则返回 None
    """
    api_config = config.get("api", {})
    return api_config.get("token")


def load_mode_config(mode: str = "标准", config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载指定模式的完整配置（预设 + 用户自定义）

    Args:
        mode: 预设模式名称（快速/标准/精细）
        config_path: 配置文件路径

    Returns:
        合并后的配置字典
    """
    config = load_config(config_path)
    preset_config = get_preset_config(config, mode)
    user_options = config.get("options", {})

    return merge_options(preset_config, user_options)
