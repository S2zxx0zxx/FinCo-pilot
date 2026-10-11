import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.legacy_preservation_manifest import EvidenceError, build_manifest


@pytest.fixture
def evidence():
    return {
        "project_id": "synthetic-project", "production_branch": "source", "restored_branch": "restore",
        "verified_at": "2026-10-11", "all_58_tables_match": False,
        "tables": [{"table_name": "users", "columns": [{"column": "user_id"}]}],
        "source_table_fingerprints": [{"table_name": "users", "row_count": "3", "row_digest": "a" * 64}],
        "restored_table_fingerprints": [{"table_name": "users", "row_count": 3, "row_digest": "a" * 64}],
    }


def test_computes_restore_proof_without_trusting_supplied_boolean(evidence):
    result = build_manifest(evidence)
    assert result["snapshot_restore_verified"] is True
    assert result["row_count"] == 3
    assert result["table_count"] == 1
    assert result["conversion_ready"] is False
    assert result["cutover_authorized"] is False
    assert result["tables"][0]["disposition"] == "unmapped_preserve_unchanged"
    assert result["tables"][0]["source_columns_requiring_mapping"] == ["user_id"]


@pytest.mark.parametrize("field", ["source_table_fingerprints", "restored_table_fingerprints", "tables"])
def test_missing_table_cannot_pass(evidence, field):
    evidence[field] = []
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


@pytest.mark.parametrize("field", ["source_table_fingerprints", "restored_table_fingerprints", "tables"])
def test_duplicate_table_cannot_hide_missing_table(evidence, field):
    evidence[field].append(copy.deepcopy(evidence[field][0]))
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


@pytest.mark.parametrize("change", ["digest", "count", "name", "same_branch"])
def test_mismatched_or_nonindependent_restore_fails(evidence, change):
    if change == "same_branch":
        evidence["restored_branch"] = evidence["production_branch"]
    else:
        row = evidence["restored_table_fingerprints"][0]
        row[{"digest": "row_digest", "count": "row_count", "name": "table_name"}[change]] = {
            "digest": "b" * 64, "count": "2", "name": "different_table",
        }[change]
    evidence["all_58_tables_match"] = True
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


@pytest.mark.parametrize("count", [-1, True, 1.5, "-1", "1.0", "NaN", "01", None])
def test_invalid_counts_are_rejected(evidence, count):
    evidence["source_table_fingerprints"][0]["row_count"] = count
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


@pytest.mark.parametrize("digest", ["", "not-a-sha", "a" * 63, "g" * 64, None])
def test_invalid_fingerprints_are_rejected(evidence, digest):
    evidence["source_table_fingerprints"][0]["row_digest"] = digest
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


def test_all_source_columns_and_unrecognized_tables_remain_visible(evidence):
    evidence["tables"][0]["columns"].append({"column": "clerk_uid"})
    evidence["tables"].append({"table_name": "unrecognized_provider_state", "columns": [{"column": "opaque_state"}]})
    for field in ["source_table_fingerprints", "restored_table_fingerprints"]:
        evidence[field].append({"table_name": "unrecognized_provider_state", "row_count": 2, "row_digest": "b" * 64})
    evidence["private_rows"] = [{"password": "never-export-this"}]
    result = build_manifest(evidence)
    assert result["row_count"] == 5
    assert result["source_column_count"] == 3
    assert result["tables"][0]["proposed_current_table"] is None
    assert "never-export-this" not in json.dumps(result)


def test_duplicate_source_column_is_rejected(evidence):
    evidence["tables"][0]["columns"].append({"column": "user_id"})
    with pytest.raises(EvidenceError):
        build_manifest(evidence)


def test_cli_redacts_parser_errors_and_fails_closed(tmp_path):
    source = tmp_path / "evidence.json"
    source.write_text('{"private": "never-export-this"')
    result = subprocess.run([sys.executable, "scripts/legacy_preservation_manifest.py", str(source)],
                            cwd=Path(__file__).parents[1], capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "never-export-this" not in result.stdout + result.stderr
    assert json.loads(result.stdout)["conversion_ready"] is False
