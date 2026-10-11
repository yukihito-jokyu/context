import { readFileSync } from "node:fs";
const config = JSON.parse(readFileSync(new URL("./config.json", import.meta.url), "utf8"));
const { before } = await import(new URL(config.beforeFile, import.meta.url));
export function runner(input) {
  if (before(input) === false) return "blocked";
  return run(input);
}
function run(input) {
  return input.target;
}
