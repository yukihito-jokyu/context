import { runner } from "./runner.mjs";
const inputs = [true, false].map(allowed => ({target:"sample.txt", allowed}));
console.log(JSON.stringify(inputs.map(input => ({input, output:runner(input)})), null, 2));
