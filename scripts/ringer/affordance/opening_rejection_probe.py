"""Create N staging sessions and count rejected openings (billed: one narration call each).

usage: opening_rejection_probe.py <n>   (needs E2E_API_BASE_URL and FREYTAG_TEST_CLOCK_TOKEN in the env)
"""

import collections
import json
import os
import sys
import time
import urllib.error
import urllib.request

STORY_ID = os.environ.get("PROBE_STORY_ID", "continuity_initiative")


def main() -> int:
    n = int(sys.argv[1])
    base = os.environ["E2E_API_BASE_URL"].rstrip("/")
    token = os.environ["FREYTAG_TEST_CLOCK_TOKEN"]
    results: collections.Counter[str] = collections.Counter()
    for i in range(n):
        request = urllib.request.Request(
            f"{base}/api/v1/session",
            data=json.dumps({"story_id": STORY_ID}).encode(),
            headers={"content-type": "application/json", "x-freytag-test-clock-token": token},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                response.read()
            results["ok"] += 1
            print(f"{i + 1}: ok", flush=True)
        except urllib.error.HTTPError as error:
            detail = error.read().decode()[:200]
            results[f"http {error.code}: {detail}"] += 1
            print(f"{i + 1}: http {error.code} {detail}", flush=True)
        time.sleep(7)
    print("## summary")
    for key, count in results.most_common():
        print(f"{count} x {key}")
    print(f"openings {n}, ok {results['ok']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
