/**
 * Browser-like smoke test: fetch page, JSON, JS; run initDeadlinesPage logic.
 * Usage: node scripts/_test_deadlines_browser.mjs http://127.0.0.1:8765
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const base = (process.argv[2] || "http://127.0.0.1:8765").replace(/\/$/, "");
const pageUrl = `${base}/deadlines/`;
const jsonUrl = new URL("../assets/data/deadlines.json", pageUrl).href;
const jsUrl = new URL("../assets/js/deadlines.js", pageUrl).href;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

async function fetchOk(url, label) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${label}: HTTP ${res.status} ${url}`);
  return res;
}

const pageRes = await fetchOk(pageUrl, "page");
const html = await pageRes.text();
if (!html.includes('id="conf-list"')) throw new Error("page missing conf-list");

const jsonRes = await fetchOk(jsonUrl, "json");
const data = await jsonRes.json();
if (!Array.isArray(data.conferences) || data.conferences.length < 10) {
  throw new Error(`bad conferences count: ${data.conferences?.length}`);
}

const jsRes = await fetchOk(jsUrl, "js");
let code = await jsRes.text();
code = code.replace(/^let CONFERENCES = \[\];\n*/m, "");

const CONFERENCES = data.conferences;
const fn = new Function(
  "CONFERENCES",
  "document",
  code +
    `
  sortConferences(CONFERENCES);
  const upcoming = CONFERENCES.filter(c => hasUpcomingOrTba(c));
  const passed = CONFERENCES.filter(c => !hasUpcomingOrTba(c));
  return { total: CONFERENCES.length, upcoming: upcoming.length, passed: passed.length };
`
);

const mockList = { innerHTML: "", childNodes: [], appendChild(el) { this.childNodes.push(el); } };
const document = {
  getElementById(id) {
    if (id === "conf-list") return mockList;
    if (id === "no-results") return { style: { display: "none" } };
    return null;
  },
  createElement() {
    return { className: "", innerHTML: "", textContent: "", appendChild() {} };
  },
  querySelectorAll(sel) {
    if (sel === ".filter-tag") {
      return [{ dataset: { tag: "all" }, classList: { add() {}, remove() {} }, addEventListener() {} }];
    }
    return [];
  },
};

// sort-only check
fn(CONFERENCES, document);

// full initDeadlinesPage (same globals as browser)
globalThis.document = document;
globalThis.window = { CONFERENCES: data.conferences };
globalThis.CONFERENCES = data.conferences;
const initFn = new Function(code + `initDeadlinesPage(); return document.getElementById('conf-list').childNodes.length;`);
const cardCount = initFn();
if (cardCount < 5) throw new Error(`Expected many rendered nodes, got ${cardCount}`);

console.log(
  "browser-smoke-ok",
  JSON.stringify({ pageUrl, jsonUrl, jsUrl, total: data.conferences.length, renderedNodes: cardCount })
);
