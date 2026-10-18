import { askPlayer } from "../../../frontend/e2e/blind-player.js";

const input = await new Promise((resolve, reject) => {
  let data = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => { data += chunk; });
  process.stdin.on("end", () => resolve(data));
  process.stdin.on("error", reject);
});

const payload = JSON.parse(input);
const command = await askPlayer({
  profile: "raw",
  transcript: payload.transcript,
  status: payload.status || "",
  cap: 1,
});
process.stdout.write(JSON.stringify({ command }) + "\n");
