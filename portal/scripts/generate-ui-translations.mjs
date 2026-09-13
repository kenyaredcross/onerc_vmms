import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const root = path.resolve("src");
const output = path.join(root, "i18n", "generated-translations.json");
const languages = ["sw", "ar", "pt", "fr"];
const attributeNames = new Set(["fallback", "title", "label", "placeholder", "aria-label"]);
const strings = new Set();

function walk(directory) {
	for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
		const file = path.join(directory, entry.name);
		if (entry.isDirectory() && entry.name !== "test" && entry.name !== "i18n") walk(file);
		else if (entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx")) extract(file);
	}
}

function useful(value) {
	const text = value.replace(/\s+/g, " ").trim();
	if (text.length < 2 || text.length > 500 || !/[A-Za-z]/.test(text)) return null;
	if (/^(https?:|\/|[.#[]|[a-z-]+:[a-z-]+|[\w-]+\.[\w.-]+$)/.test(text)) return null;
	return text;
}

function extract(file) {
	const source = ts.createSourceFile(file, fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
	function visit(node) {
		if (ts.isJsxText(node)) {
			const text = useful(node.getText(source));
			if (text) strings.add(text);
		}
		if (ts.isJsxAttribute(node) && attributeNames.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) {
			const text = useful(node.initializer.text);
			if (text) strings.add(text);
		}
		if ((ts.isPropertyAssignment(node) || ts.isVariableDeclaration(node)) && node.initializer && ts.isStringLiteral(node.initializer)) {
			const name = node.name?.getText(source).replace(/["']/g, "");
			if (["title", "label", "body", "note", "description", "eyebrow", "heading", "empty", "fallback", "meta"].includes(name)) {
				const text = useful(node.initializer.text);
				if (text) strings.add(text);
			}
		}
		ts.forEachChild(node, visit);
	}
	visit(source);
}

async function translate(text, language) {
	const query = new URLSearchParams({ client: "dict-chrome-ex", sl: "en", tl: language, q: text });
	for (let attempt = 0; attempt < 4; attempt++) {
		const response = await fetch(`https://clients5.google.com/translate_a/t?${query}`);
		if (response.ok) {
			const result = await response.json();
			if (typeof result?.[0] === "string") return result[0];
		}
		await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
	}
	throw new Error(`Could not translate ${language}: ${text}`);
}

walk(root);
const catalogue = fs.existsSync(output) ? JSON.parse(fs.readFileSync(output, "utf8")) : {};
for (const language of languages) catalogue[language] ||= {};
const source = [...strings].sort();

if (process.argv.includes("--check")) {
	const missing = languages.flatMap((language) => source
		.filter((text) => !catalogue[language]?.[text])
		.map((text) => `${language}: ${text}`));
	if (missing.length) {
		console.error(`Missing ${missing.length} UI translations:\n${missing.slice(0, 30).join("\n")}`);
		process.exit(1);
	}
	console.log(`Translation coverage complete: ${source.length} strings × ${languages.length} languages.`);
	process.exit(0);
}

for (const language of languages) {
	const missing = source.filter((text) => !catalogue[language][text]);
	for (let index = 0; index < missing.length; index += 10) {
		const batch = missing.slice(index, index + 10);
		const translated = await Promise.all(batch.map((text) => translate(text, language)));
		batch.forEach((text, item) => { catalogue[language][text] = translated[item]; });
		fs.writeFileSync(output, `${JSON.stringify(catalogue, null, 2)}\n`);
	}
}

console.log(`Translated ${source.length} portal strings into ${languages.length} languages.`);
