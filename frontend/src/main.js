import "./styles.css";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
const DEPLOYMENT_CHANNEL = (import.meta.env.VITE_DEPLOYMENT_CHANNEL || "production").trim();
const DEFAULT_SESSION_PAYLOAD = {
  seed: 123,
  genre: "mystery",
  session_length: "short",
  tone: "dark",
};

const transcriptElement = document.querySelector("#transcript");
const statusLineElement = document.querySelector("#status-line");
const commandFormElement = document.querySelector("#command-form");
const commandInputElement = document.querySelector("#command-input");
const sendButtonElement = document.querySelector("#send-button");
const newGameButtonElement = document.querySelector("#new-game-button");
const nonProductionBadgeElement = document.querySelector("#non-production-badge");

let sessionId = "";
let busy = false;

if (DEPLOYMENT_CHANNEL !== "production") {
  nonProductionBadgeElement.hidden = false;
}

function setBusy(nextBusy) {
  busy = nextBusy;
  commandInputElement.disabled = nextBusy;
  sendButtonElement.disabled = nextBusy || !sessionId;
  newGameButtonElement.disabled = nextBusy;
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

async function createSession() {
  setBusy(true);
  setStatus("Creating session...");
  try {
    const payload = await apiRequest("/api/v1/session", DEFAULT_SESSION_PAYLOAD);
    sessionId = payload.session_id;
    setStatus(`Session ${sessionId.slice(0, 8)} ready`);
    resetTranscript();
    renderOpening(payload.state.opening);
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
  appendEntry(opening.scene, "output");
  appendEntry(
    [opening.protagonist_context, opening.arrival_context, ...opening.public_briefing]
      .filter((line) => typeof line === "string" && line.length > 0)
      .join("\n\n"),
    "output",
  );
  if (Array.isArray(opening.first_available_actions) && opening.first_available_actions.length > 0) {
    appendEntry(`Try: ${opening.first_available_actions.join(" • ")}`, "system");
  }
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
      genre: DEFAULT_SESSION_PAYLOAD.genre,
      command,
    });
    const lines = Array.isArray(payload.lines) ? payload.lines : [];
    appendEntry(lines.join("\n"), "output");
    const destinations = payload.state.available_destinations;
    if (Array.isArray(destinations) && destinations.length > 0) {
      appendEntry(`Accessible from here: ${destinations.join(", ")}.`, "system");
    }
    setStatus(`${payload.state.room_name} • turn ${payload.state.turn_index}`);
  } catch (error) {
    appendEntry(error instanceof Error ? error.message : "Command failed.", "system");
    setStatus(error instanceof Error ? error.message : "Command failed.", "error");
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

createSession();
