#!/usr/bin/env node

/**
 * WSL entry point for the VMMS route-capture utility.
 *
 * Edge runs on Windows, and its DevTools port is not reliably forwarded back
 * into WSL. The PowerShell helper therefore speaks DevTools on Windows while
 * this wrapper keeps the npm command, Linux paths and validation convenient.
 */

import { execFileSync, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

function argumentsOf(argv) {
	const values = {};

	for (const token of argv) {
		if (!token.startsWith("--")) continue;

		const [rawKey, ...rest] = token.slice(2).split("=");
		values[rawKey] = rest.length ? rest.join("=") : true;
	}

	return values;
}

function positiveNumber(value, fallback, name) {
	if (value === undefined) return fallback;

	const parsed = Number(value);
	if (!Number.isFinite(parsed) || parsed <= 0) {
		throw new Error(`--${name} must be a positive number`);
	}

	return String(parsed);
}

function windowsPath(value) {
	return execFileSync("wslpath", ["-w", value], { encoding: "utf8" }).trim();
}

function main() {
	const args = argumentsOf(process.argv.slice(2));
	const url = args.url;

	if (!url || typeof url !== "string") throw new Error("--url is required");

	const here = path.dirname(fileURLToPath(import.meta.url));
	const helper = windowsPath(path.join(here, "capture-route.ps1"));
	const output = args.output ?? "/tmp/vmms-route.png";
	const command = [
		"-NoProfile",
		"-ExecutionPolicy",
		"Bypass",
		"-File",
		helper,
		"-Url",
		url,
		"-Output",
		output.startsWith("/") ? windowsPath(output) : output,
		"-Width",
		positiveNumber(args.width, 1440, "width"),
		"-Height",
		positiveNumber(args.height, 1000, "height"),
		"-WaitMilliseconds",
		positiveNumber(args.wait, 8000, "wait"),
	];

	if (args.mobile) command.push("-Mobile");
	if (args["full-page"]) command.push("-FullPage");
	if (args.prepare) command.push("-Prepare", args.prepare);
	if (args.edge) command.push("-Edge", args.edge);
	// An authenticated capture: the value is a Frappe `sid` cookie minted with
	// `curl -c` against `/api/method/login`. Set on the host before navigation so
	// an auth-gated route (the portal, the console) renders signed in rather than
	// bouncing to the login page.
	if (args.sid) command.push("-Sid", args.sid);
	if (args.host) command.push("-CookieHost", args.host);

	const result = spawnSync(
		"/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe",
		command,
		{ stdio: "inherit" },
	);

	if (result.error) throw result.error;
	process.exitCode = result.status ?? 1;
}

try {
	main();
} catch (error) {
	process.stderr.write(`${error.stack ?? error.message}\n`);
	process.exitCode = 1;
}
