import { askPlayer } from "../../../frontend/e2e/blind-player.js";

const input = await new Promise((resolve, reject) => {
  let data = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => { data += chunk; });
  process.stdin.on("end", () => resolve(data));
  process.stdin.on("error", reject);
});
const payload = JSON.parse(input);
if (payload.playerPrompt !== undefined) {
  process.stdout.write(JSON.stringify({ command: payload.playerPrompt, attempts: 0, offline: true }) + "\n");
} else {
  const command = await askPlayer({ profile: "raw", transcript: payload.transcript, status: payload.status || "", cap: 1 });
  process.stdout.write(JSON.stringify({ command, attempts: 1 }) + "\n");
}
