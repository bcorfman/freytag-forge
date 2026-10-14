"""Check for a hosted @spine run: fresh artifact, expected SHA on staging, print delivery telemetry."""
import json, os, sys, time, urllib.request
root, sha = sys.argv[1], sys.argv[2]
env = dict(l.strip().split("=", 1) for l in open(os.path.join(root, ".env")) if "=" in l and not l.startswith("#"))
base = env["E2E_API_BASE_URL"].strip("'\"")
live = json.load(urllib.request.urlopen(base + "/api/v1/version"))
if not live["sha"].startswith(sha):
    sys.exit(f"FAIL staging reports {live['sha']}, expected {sha}")
path = os.path.join(root, "artifacts/e2e-spine.json")
if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 3600:
    sys.exit("FAIL no fresh e2e-spine.json: the run did not finish (or the test failed before writing it)")
d = json.load(open(path))
print(json.dumps({k: v for k, v in d.items() if not isinstance(v, (list, dict))}, indent=1))
for k, v in d.items():
    if isinstance(v, (list, dict)):
        print(k, "->", json.dumps(v)[:1500])
print("PASS")
