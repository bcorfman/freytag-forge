const DEFAULT_MAX_TOKENS_CEILING = 2048;

// The 70B narrator is more reliable with default sampling, so this profile ignores response_format.
function buildLlamaPlainBody({ system, user, maxTokens }) {
  return {
    messages: [
      { role: "system", content: system },
      { role: "user", content: user }
    ],
    max_tokens: maxTokens
  };
}

function legacyText(payload) {
  for (const value of [payload?.result?.response, payload?.result?.text, payload?.response]) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (value && typeof value === "object") return JSON.stringify(value);
  }
  return "";
}

function usage(candidate) {
  return {
    promptTokens: Number.isFinite(candidate?.prompt_tokens) ? candidate.prompt_tokens : null,
    completionTokens: Number.isFinite(candidate?.completion_tokens) ? candidate.completion_tokens : null
  };
}

function extractLlama(payload) {
  // Keep the legacy accounting path: the old handler only read result.usage.
  const tokens = usage(payload?.result?.usage);
  return {
    text: legacyText(payload),
    promptTokens: tokens.promptTokens,
    completionTokens: tokens.completionTokens,
    truncated: false
  };
}

export const MODEL_PROFILES = {
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {
    buildBody: buildLlamaPlainBody,
    extract: extractLlama,
    maxTokensCeiling: DEFAULT_MAX_TOKENS_CEILING,
    price: { input: 0.293, output: 2.253 }
  }
};

export function getModelProfile(model) {
  return MODEL_PROFILES[model] || MODEL_PROFILES["@cf/meta/llama-3.3-70b-instruct-fp8-fast"];
}
