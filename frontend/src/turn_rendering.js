export function turnBlocks(payload) {
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  const segments = Array.isArray(payload.segments) ? payload.segments : [];
  if (segments.length === 0) {
    return lines
      .filter((line) => typeof line === "string" && line.length > 0)
      .map((text) => ({ kind: "narration", text }));
  }
  const blocks = [];
  if (typeof lines[0] === "string" && lines[0].length > 0) {
    blocks.push({ kind: "narration", text: lines[0] });
  }
  return blocks.concat(segments);
}
