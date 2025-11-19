"""Utility helpers shared across pipelines."""

import os
from typing import Dict


def _normalize_dir(path: str) -> str:
    """Ensure directory-style paths with trailing slash."""
    if path.endswith(".csv"):
        path = os.path.dirname(path)
    path = path.rstrip("/")
    return f"{path}/"


def _swap_layer(path: str, dataset_key: str, new_layer: str) -> str:
    """Replace known layer folder names or append a new structure."""
    for layer in ("raw", "source", "bronze", "archive", "quarantine"):
        marker = f"/{layer}/"
        if marker in path:
            return path.replace(marker, f"/{new_layer}/")
    parent = os.path.dirname(path.rstrip("/")) or "/"
    return _normalize_dir(os.path.join(parent, new_layer, dataset_key))


def resolve_medallion_paths(dataset_key: str, config_section: Dict[str, str]) -> Dict[str, str]:
    """Resolve source/bronze/archive/quarantine paths from minimal config."""
    input_path = config_section.get("input_path")
    if not input_path:
        raise ValueError(f"Missing input_path for {dataset_key}")

    source_path = _normalize_dir(config_section.get("source_path", input_path))
    bronze_path = _normalize_dir(config_section.get("bronze_path") or _swap_layer(source_path, dataset_key, "bronze"))
    archive_path = _normalize_dir(config_section.get("archive_path") or _swap_layer(bronze_path, dataset_key, "archive"))
    quarantine_path = _normalize_dir(config_section.get("quarantine_path") or _swap_layer(source_path, dataset_key, "quarantine"))
    hudi_output_path = _normalize_dir(config_section["hudi_output_path"])

    return {
        "source": source_path,
        "bronze": bronze_path,
        "archive": archive_path,
        "quarantine": quarantine_path,
        "hudi": hudi_output_path,
    }


def ensure_dir(path: str) -> str:
    """Create directory if missing and return normalized path."""
    os.makedirs(path, exist_ok=True)
    return path
