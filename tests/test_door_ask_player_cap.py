import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHILD = ROOT / "scripts/ringer/stage7/door_ask_player.mjs"


@pytest.fixture(scope="module")
def node() -> str:
    executable = shutil.which("node")
    if executable is None:
        pytest.skip("node is required for the door ask-player cap tests")
    return executable


@pytest.fixture(scope="module")
def fetch_stub(tmp_path_factory: pytest.TempPathFactory) -> Path:
    stub = tmp_path_factory.mktemp("node-fetch-stub") / "fetch-stub.mjs"
    stub.write_text(
        """
const replies = JSON.parse(process.env.STUB_RESPONSES);
let calls = 0;
globalThis.fetch = async () => {
  const index = calls++;
  await import("node:fs/promises").then((fs) => fs.writeFile(process.env.STUB_COUNT_FILE, String(calls)));
  return {
    ok: true,
    status: 200,
    json: async () => ({ output_text: JSON.stringify({ command: replies[index] }) }),
  };
};
""".strip()
        + "\n"
    )
    return stub


def run_child(node: str, fetch_stub: Path, tmp_path: Path, replies: list[str]) -> subprocess.CompletedProcess[str]:
    count_file = tmp_path / "fetch-count"
    environment = {
        **os.environ,
        "OPENAI_API_KEY": "dummy",
        "STUB_RESPONSES": json.dumps(replies),
        "STUB_COUNT_FILE": str(count_file),
    }
    return subprocess.run(
        [node, "--import", str(fetch_stub), str(CHILD)],
        cwd=ROOT,
        env=environment,
        input=json.dumps({"transcript": "A plain room.", "status": ""}),
        text=True,
        capture_output=True,
        check=False,
    )


def fetch_count(result: subprocess.CompletedProcess[str], tmp_path: Path) -> int:
    return int((tmp_path / "fetch-count").read_text())


def test_valid_first_reply_uses_one_fetch(node: str, fetch_stub: Path, tmp_path: Path) -> None:
    result = run_child(node, fetch_stub, tmp_path, ["Search the desk"])

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"command": "Search the desk", "attempts": 1}
    assert fetch_count(result, tmp_path) == 1


def test_invalid_first_reply_retries_once(node: str, fetch_stub: Path, tmp_path: Path) -> None:
    result = run_child(node, fetch_stub, tmp_path, ["Search the desk.\nThen look.", "Search the desk"])

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"command": "Search the desk", "attempts": 1}
    assert fetch_count(result, tmp_path) == 2


def test_two_invalid_replies_hit_cap(node: str, fetch_stub: Path, tmp_path: Path) -> None:
    result = run_child(node, fetch_stub, tmp_path, ["Search the desk.\nThen look.", "Search the desk.\nThen look."])

    assert result.returncode != 0
    assert "Blind player returned an invalid command twice" in result.stderr
    assert fetch_count(result, tmp_path) == 2
