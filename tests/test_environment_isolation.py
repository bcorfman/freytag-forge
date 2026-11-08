import os

pytest_plugins = ["pytester"]


def test_environment_isolation_between_tests(pytester):
    original_value = os.environ.get("PATH")
    pytester.makeconftest('pytest_plugins = ["tests.conftest"]')
    pytester.makepyfile(
        test_environment_probe="""
import os


def test_a_mutates_environment():
    os.environ["FREYTAG_ISOLATION_PROBE"] = "1"
    os.environ["PATH_PROBE_REMOVED"] = "present"
    del os.environ["PATH_PROBE_REMOVED"]
    os.environ["PATH"] = "changed"


def test_b_sees_original_environment():
    assert "FREYTAG_ISOLATION_PROBE" not in os.environ
    assert "PATH_PROBE_REMOVED" not in os.environ
    assert os.environ["PATH"] == ORIGINAL_PATH
""".replace("ORIGINAL_PATH", repr(original_value)),
    )
    result = pytester.runpytest("-p", "no:randomly", "-n", "0")
    result.assert_outcomes(passed=2)
