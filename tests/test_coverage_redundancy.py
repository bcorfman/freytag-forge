import json

from coverage import CoverageData

from scripts import coverage_redundancy


def _coverage_file(path, contexts):
    data = CoverageData(basename=str(path))
    for context, lines in contexts.items():
        data.set_context(context)
        data.add_lines({"app.py": set(lines)})
    data.write()
    return path


def _report(tmp_path, contexts):
    data_path = _coverage_file(tmp_path / "input.coverage", contexts)
    output_path = tmp_path / "report.json"
    assert coverage_redundancy.main([str(data_path), "--out", str(output_path)]) == 0
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_reports_subsets_identical_groups_private_lines_and_phase_merging(tmp_path):
    report = _report(
        tmp_path,
        {
            "tests/test_redundant.py::test_subset|run": [1, 2],
            "tests/test_redundant.py::test_superset|run": [1, 2, 3],
            "tests/test_redundant.py::test_identical_a|run": [4, 5],
            "tests/test_redundant.py::test_identical_b|run": [4, 5],
            "tests/test_redundant.py::test_phases|setup": [6],
            "tests/test_redundant.py::test_phases|run": [7],
            "tests/test_redundant.py::test_private|run": [3, 8],
        },
    )

    assert report["tests"] == 6
    assert "tests/test_redundant.py::test_subset" in report["no_unique_lines"]
    subset = next(item for item in report["per_test"] if item["id"].endswith("::test_subset"))
    assert subset["subset_of"] == ["tests/test_redundant.py::test_superset"]
    assert ["tests/test_redundant.py::test_identical_a", "tests/test_redundant.py::test_identical_b"] in report[
        "identical_groups"
    ]
    private = next(item for item in report["per_test"] if item["id"].endswith("::test_private"))
    assert private["unique_lines"] == 1
    phases = next(item for item in report["per_test"] if item["id"].endswith("::test_phases"))
    assert phases["lines"] == 2


def test_missing_coverage_file_exits_two(tmp_path, capsys):
    output_path = tmp_path / "report.json"
    assert coverage_redundancy.main([str(tmp_path / "missing.coverage"), "--out", str(output_path)]) == 2
    assert "missing or empty" in capsys.readouterr().err
