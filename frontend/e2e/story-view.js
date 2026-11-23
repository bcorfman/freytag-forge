import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const views = new Map();

export function loadAuthoringView(root = resolve(import.meta.dirname, "../..")) {
  const resolvedRoot = resolve(root);
  if (views.has(resolvedRoot)) return views.get(resolvedRoot);

  const python = process.env.FREYTAG_PYTHON || (
    existsSync(resolve(resolvedRoot, ".venv", "bin", "python"))
      ? resolve(resolvedRoot, ".venv", "bin", "python")
      : "python3"
  );
  const args = ["-m", "storygame.story_package.authoring_view", "data/stories/continuity-initiative"];
  const command = [python, ...args].join(" ");
  const existingPythonPath = process.env.PYTHONPATH;
  const pythonPath = [existingPythonPath, resolvedRoot, resolve(resolvedRoot, "packages/worldkeeper/src")]
    .filter(Boolean)
    .join(":");
  const result = spawnSync(python, args, {
    cwd: resolvedRoot,
    env: { ...process.env, PYTHONPATH: pythonPath },
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const status = result.status === null ? `signal ${result.signal}` : result.status;
  if (result.status !== 0) {
    const stderr = (result.stderr || "").slice(-400);
    throw new Error(`${command} failed with exit status ${status}: ${stderr}`);
  }

  let view;
  try {
    view = JSON.parse(result.stdout);
  } catch (error) {
    const stderr = (result.stderr || "").slice(-400);
    throw new Error(`${command} failed with exit status ${status}: ${stderr}`);
  }
  views.set(resolvedRoot, view);
  return view;
}
