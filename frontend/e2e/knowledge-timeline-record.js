function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function headerValue(headers, name) {
  if (!headers) return null;
  if (typeof headers.get === "function") return headers.get(name) ?? null;
  const wanted = name.toLowerCase();
  const key = Object.keys(headers).find((candidate) => candidate.toLowerCase() === wanted);
  return key ? headers[key] ?? null : null;
}

export function recordTurnOutcome({ input, status, headers, body, version }) {
  const audit = body && typeof body === "object" && body.knowledge_audit && typeof body.knowledge_audit === "object"
    ? body.knowledge_audit
    : null;
  const acceptedSegments = asArray(audit?.accepted_segments).map((segment) => ({
    kind: segment?.kind ?? null,
    speaker_id: segment?.speaker_id ?? null,
    grounding_ids: asArray(segment?.grounding_ids),
  }));
  return {
    deployment_sha: version && typeof version === "object" ? version.sha ?? null : null,
    input: input ?? null,
    context_candidate_ids: asArray(audit?.context_candidate_ids),
    provider_selected_ids: asArray(audit?.provider_selected_ids),
    resolved_source_ids: asArray(audit?.resolved_source_ids),
    accepted_segments: acceptedSegments,
    result: audit?.result ?? null,
    rejection_code: audit?.rejection_code ?? headerValue(headers, "X-Freytag-Rejection-Code"),
    recovery_used: audit?.recovery_used ?? null,
    status: status ?? null,
  };
}

export function buildKnowledgeTimelineReport(version, records) {
  return {
    deployment_sha: version && typeof version === "object" ? version.sha ?? null : null,
    channel: version && typeof version === "object" ? version.channel ?? null : null,
    records: asArray(records),
  };
}
