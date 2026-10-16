import json
import zipfile

from scripts.check_artifact_secret_hygiene import inspect_artifact
from scripts.check_secret_hygiene import ROOT, scan_token_patterns


def synthetic_pattern():
    # Construct detector input without committing a complete credential pattern.
    return "gh" + "p_" + "a" * 36


def test_example_words_do_not_suppress_a_credential_pattern():
    token = synthetic_pattern()
    found = scan_token_patterns(ROOT / "synthetic.example", "example synthetic your-key " + token)
    assert len(found) == 1
    assert token not in "\n".join(found)


def test_zip_scan_never_extracts_or_discloses_values(tmp_path):
    token = synthetic_pattern()
    archive = tmp_path / "artifact.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../outside.env", "example=" + token)
        output.writestr("picture.png", b"\x89PNG\0\xff")
    report = inspect_artifact(archive)
    assert report["findings"] == [{"member": 1, "line": 1, "type": "GitHub token"}]
    assert report["binary_files_excluded"] == 1
    assert not (tmp_path.parent / "outside.env").exists()
    assert token not in json.dumps(report)


def test_zip_limits_and_missing_files_do_not_become_clean_results(tmp_path):
    archive = tmp_path / "oversize.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("large.txt", "x" * 65)
    assert inspect_artifact(archive, max_member=64)["errors"]
    assert inspect_artifact(archive, max_total=64)["errors"]
    assert inspect_artifact(tmp_path / "missing.zip")["errors"]
