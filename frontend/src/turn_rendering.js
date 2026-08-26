export function turnBlocks(payload) {
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  const segments = Array.isArray(payload.segments) ? payload.segments : [];
  if (segments.length === 0) {
    return lines
      .filter((line) => typeof line === "string" && line.length > 0)
      .map((text) => ({ kind: "narration", text }));
  }
  return segments.filter((segment) => segment && typeof segment.text === "string" && segment.text.length > 0);
}
