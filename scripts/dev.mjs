import { spawn } from "node:child_process";
import { existsSync } from "node:fs";

const uvicornArgs = [
  "server.dev_app:app",
  "--reload",
  ...(existsSync(".env") ? ["--env-file", ".env"] : []),
  "--host",
  "0.0.0.0",
  "--port",
  "6000",
];

const processes = [
  spawn("server/.venv/bin/uvicorn", uvicornArgs, {
    stdio: "inherit",
    env: { ...process.env, BROWSER_DEV_MODE: "true" },
  }),
  spawn("npm", ["run", "start-react"], { stdio: "inherit" }),
];

let stopping = false;

const stopAll = (signal = "SIGTERM") => {
  if (stopping) return;
  stopping = true;
  for (const child of processes) {
    if (!child.killed) child.kill(signal);
  }
};

for (const child of processes) {
  child.on("exit", (code) => {
    if (!stopping && code !== 0) {
      stopAll();
      process.exitCode = code ?? 1;
    }
  });
}

process.on("SIGINT", () => stopAll("SIGINT"));
process.on("SIGTERM", () => stopAll("SIGTERM"));
