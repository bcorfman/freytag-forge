"""Ringer check helper: the runtime bench path must hand mark_fixed to build_capture_provider."""
import sys

core = open("bench/core.py").read()
cap = open("storygame/runtime/capture.py").read()
if core.count("build_capture_provider(") < 3:
    sys.exit("FAIL expected the import plus two call sites of build_capture_provider in bench/core.py")
calls = [line for line in core.splitlines() if "build_capture_provider(" in line and "import" not in line]
if not calls or any("mark_fixed" not in line for line in calls):
    sys.exit("FAIL a build_capture_provider call in bench/core.py does not pass mark_fixed: " + repr(calls))
if "mark_fixed" not in cap:
    sys.exit("FAIL capture.build_capture_provider does not accept mark_fixed")
print("runtime marker plumbing ok")
