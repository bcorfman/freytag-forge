const DEFAULT_MAX_TOKENS_CEILING = 2048;

function buildLlamaBody({ system, user, maxTokens, responseFormat }) {
  return {
    messages: [
      { role: "system", content: system },
      { role: "user", content: user }
    ],
    max_tokens: maxTokens,
    ...(responseFormat ? { response_format: responseFormat, temperature: 0 } : {})
  };
}

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

function buildDeepseekBody({ system, user, maxTokens, responseFormat }) {
  return {
    messages: [
      { role: "system", content: system },
      { role: "user", content: user }
    ],
    max_completion_tokens: maxTokens,
    reasoning_effort: "low",
    ...(responseFormat ? { response_format: responseFormat, temperature: 0 } : {})
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

function extractDeepseek(payload) {
  const result = payload?.result && typeof payload.result === "object" ? payload.result : payload;
  const choice = Array.isArray(result?.choices) ? result.choices[0] : null;
  const content = choice?.message?.content;
  const tokens = usage(result?.usage ?? payload?.usage);
  return {
    text: typeof content === "string" && content.trim() ? content.trim() : "",
    promptTokens: tokens.promptTokens,
    completionTokens: tokens.completionTokens,
    truncated: choice?.finish_reason === "length"
  };
}

export const MODEL_PROFILES = {
  "@cf/meta/llama-3.1-8b-instruct-fast": {
    buildBody: buildLlamaBody,
    extract: extractLlama,
    maxTokensCeiling: DEFAULT_MAX_TOKENS_CEILING,
    price: { input: 0.282, output: 0.827 }
  },
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {
    buildBody: buildLlamaPlainBody,
    extract: extractLlama,
    maxTokensCeiling: DEFAULT_MAX_TOKENS_CEILING,
    price: { input: 0.293, output: 2.253 }
  },
  "@cf/deepseek-ai/deepseek-v4.1-flash-1017": {
    buildBody: buildDeepseekBody,
    extract: extractDeepseek,
    maxTokensCeiling: 4096,
    price: { input: 0.3, output: 1.2 }
  }
};

export function getModelProfile(model) {
  return MODEL_PROFILES[model] || MODEL_PROFILES["@cf/meta/llama-3.1-8b-instruct-fast"];
}
