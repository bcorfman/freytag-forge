function trimmedText(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function partitionTransitionSegments(segments, { sourceSceneId, targetSceneId, authored }) {
  if (sourceSceneId === targetSceneId) {
    return { departure: [...segments], arrival: [], method: "none" };
  }

  const bridge = authored?.bridgeTextsByScenePair?.get(`${sourceSceneId}>${targetSceneId}`);
  const bridgeText = trimmedText(bridge);
  if (bridgeText) {
    let bridgeIndex = -1;
    for (let index = 0; index < segments.length; index += 1) {
      if (trimmedText(segments[index]?.text) === bridgeText) bridgeIndex = index;
    }
    if (bridgeIndex >= 0) {
      return {
        departure: segments.slice(0, bridgeIndex + 1),
        arrival: segments.slice(bridgeIndex + 1),
        method: "bridge",
      };
    }
  }

  const entryTexts = new Set();
  const entry = authored?.entryTexts?.get(targetSceneId);
  if (entry) entryTexts.add(trimmedText(entry));
  for (const variant of authored?.entryVariantTextsBySceneId?.get(targetSceneId) || []) {
    const text = trimmedText(variant);
    if (text) entryTexts.add(text);
  }
  const entryIndex = segments.findIndex((segment) => entryTexts.has(trimmedText(segment?.text)));
  if (entryIndex >= 0) {
    return {
      departure: segments.slice(0, entryIndex),
      arrival: segments.slice(entryIndex),
      method: "entry",
    };
  }

  return {
    departure: segments.slice(0, -1),
    arrival: segments.slice(-1),
    method: "fallback",
  };
}
