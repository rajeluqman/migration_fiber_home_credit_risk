"""Placeholder unit tests — this repo is a governance-framework port (ADR-005/006), no real
Fabric notebook transform code has been written yet. Real tests land alongside
notebooks/nb_silver_*.py per learning/CURRICULUM.md M2-M3 (mirrors parent repo's
tests/unit/test_silver_transforms.py once ported).
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_notebooks_dir_exists():
    assert (REPO / "notebooks").is_dir()


def test_dbt_fabric_project_root_exists():
    assert (REPO / "dbt_fabric").is_dir()


def test_migration_provenance_folder_exists():
    assert (REPO / "migration").is_dir()
