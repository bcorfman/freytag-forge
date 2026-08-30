import "./styles.css";
import { turnBlocks } from "./turn_rendering.js";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
const DEPLOYMENT_CHANNEL = (import.meta.env.VITE_DEPLOYMENT_CHANNEL || "production").trim();
const DEFAULT_SESSION_PAYLOAD = { story_id: "continuity_initiative" };

const transcriptElement = document.querySelector("#transcript");
const statusLineElement = document.querySelector("#status-line");
const commandFormElement = document.querySelector("#command-form");
const commandInputElement = document.querySelector("#command-input");
const sendButtonElement = document.querySelector("#send-button");
const newGameButtonElement = document.querySelector("#new-game-button");
const nonProductionBadgeElement = document.querySelector("#non-production-badge");
const gameBreakPanelElement = document.querySelector("#game-break-panel");
const gameBreakReasonElement = document.querySelector("#game-break-reason");
const proceedButtonElement = document.querySelector("#proceed-button");
const returnToSceneButtonElement = document.querySelector("#return-to-scene-button");

let sessionId = "";
let busy = false;
let pendingGameBreak = null;

if (DEPLOYMENT_CHANNEL !== "production") {
  nonProductionBadgeElement.hidden = false;
}

function setBusy(nextBusy) {
  busy = nextBusy;
  commandInputElement.disabled = nextBusy || Boolean(pendingGameBreak);
  sendButtonElement.disabled = nextBusy || !sessionId;
  newGameButtonElement.disabled = nextBusy;
}

function setGameBreak(gameBreak) {
  pendingGameBreak = gameBreak || null;
  gameBreakPanelElement.hidden = !pendingGameBreak;
  if (pendingGameBreak) {
    gameBreakReasonElement.textContent = pendingGameBreak.reason;
  }
  setBusy(busy);
}

function setStatus(text, kind = "normal") {
  statusLineElement.textContent = text;
  statusLineElement.dataset.kind = kind;
}

function appendEntry(text, kind = "output") {
  const entry = document.createElement("pre");
  entry.className = `entry entry-${kind}`;
  entry.textContent = text;
  transcriptElement.append(entry);
  transcriptElement.scrollTop = transcriptElement.scrollHeight;
}

function appendSegment(segment) {
  if (!segment || typeof segment !== "object" || typeof segment.text !== "string") {
    return;
  }
  const entry = document.createElement("article");
  entry.className = `entry entry-${segment.kind}`;

  if (segment.kind === "speech" && segment.speaker && typeof segment.speaker.name === "string") {
    const attribution = document.createElement("p");
    attribution.className = "segment-attribution";
    attribution.textContent = segment.speaker.name;
    const quote = document.createElement("blockquote");
    quote.className = "segment-speech";
    quote.textContent = segment.text;
    entry.append(attribution, quote);
  } else if (segment.kind === "action" && segment.actor && typeof segment.actor.name === "string") {
    entry.classList.add(`entry-action-${segment.grounding || "expressive"}`);
    entry.setAttribute("aria-label", `Stage direction by ${segment.actor.name}`);
    entry.textContent = `${segment.actor.name} — ${segment.text}`;
  } else {
    return;
  }

  transcriptElement.append(entry);
  transcriptElement.scrollTop = transcriptElement.scrollHeight;
}

function renderTurn(payload) {
  turnBlocks(payload).forEach((block) => {
    if (block.kind === "narration") {
      appendEntry(block.text, "output");
    } else {
      appendSegment(block);
    }
  });
  setGameBreak(payload.game_break);
}

function resetTranscript() {
  transcriptElement.replaceChildren();
}

async function apiRequest(path, payload) {
  if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Request failed.";
    throw new Error(detail);
  }
  return data;
}

async function apiGet(path) {
  if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const response = await fetch(`${API_BASE_URL}${path}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Service identity check failed.");
  }
  return data;
}

async function createSession() {
  setBusy(true);
  setStatus("Creating session...");
  try {
    const identity = await apiGet("/api/v1/version");
    if (identity.api !== "v1" || identity.runtime !== "scene-v1" || identity.channel !== DEPLOYMENT_CHANNEL) {
      throw new Error("The story service is on a different deployment channel. Refresh and try again.");
    }
    const payload = await apiRequest("/api/v1/session", DEFAULT_SESSION_PAYLOAD);
    sessionId = payload.session_id;
    setStatus(`Scene ${payload.state.scene_id} • ${payload.state.phase.replaceAll("_", " ")}`);
    resetTranscript();
    renderOpening(payload.opening);
    setGameBreak(null);
  } catch (error) {
    sessionId = "";
    setStatus(error instanceof Error ? error.message : "Session creation failed.", "error");
  } finally {
    setBusy(false);
    commandInputElement.focus();
  }
}

function renderOpening(opening) {
  if (!opening || typeof opening !== "object") {
    return;
  }
  appendEntry(opening.text, "output");
}

async function runCommand(command, echoInput = true) {
  if (!sessionId) {
    throw new Error("No session available.");
  }

  if (echoInput) {
    appendEntry(command, "input");
  }
  setBusy(true);
  setStatus("Awaiting reply...");
  try {
    const payload = await apiRequest("/api/v1/turn", {
      session_id: sessionId,
      player_input: command,
    });
    renderTurn(payload);
    setStatus(`Scene ${payload.state.scene_id} • ${payload.state.phase.replaceAll("_", " ")}`);
  } catch (error) {
    appendEntry(error instanceof Error ? error.message : "Command failed.", "system");
    setStatus(error instanceof Error ? error.message : "Command failed.", "error");
  } finally {
    setBusy(false);
    commandInputElement.focus();
  }
}

async function resolveGameBreak(decision) {
  if (!sessionId || !pendingGameBreak || busy) {
    return;
  }
  setBusy(true);
  try {
    const payload = await apiRequest("/api/v1/game-break", {
      session_id: sessionId,
      warning_id: pendingGameBreak.warning_id,
      decision,
    });
    renderTurn(payload);
    setStatus(`Scene ${payload.state.scene_id} • ${payload.state.phase.replaceAll("_", " ")}`);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not resolve the warning.", "error");
  } finally {
    setBusy(false);
    commandInputElement.focus();
  }
}

commandFormElement.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) {
    return;
  }

  const command = commandInputElement.value.trim();
  if (!command) {
    return;
  }

  commandInputElement.value = "";
  await runCommand(command);
});

newGameButtonElement.addEventListener("click", async () => {
  if (busy) {
    return;
  }
  await createSession();
});

proceedButtonElement.addEventListener("click", () => resolveGameBreak("proceed"));
returnToSceneButtonElement.addEventListener("click", () => resolveGameBreak("return_to_scene"));

createSession();
