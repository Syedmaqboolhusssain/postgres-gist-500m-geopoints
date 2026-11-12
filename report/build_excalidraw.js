const fs = require("fs");
const path = require("path");

const outDir = path.join(__dirname, "..", "output", "excalidraw");
fs.mkdirSync(outDir, { recursive: true });

let seq = 0;
const elements = [];
const now = 1794459600000;

function base(type, id, x, y, width, height, opts = {}) {
  seq += 1;
  return {
    id,
    type,
    x,
    y,
    width,
    height,
    angle: 0,
    strokeColor: opts.strokeColor || "#1e1e1e",
    backgroundColor: opts.backgroundColor || "transparent",
    fillStyle: "solid",
    strokeWidth: opts.strokeWidth || 2,
    strokeStyle: opts.strokeStyle || "solid",
    roughness: opts.roughness ?? 1,
    opacity: 100,
    groupIds: opts.groupIds || [],
    frameId: null,
    index: `a${String(seq).padStart(3, "0")}`,
    roundness: type === "rectangle" ? { type: 3 } : null,
    seed: 1000 + seq * 97,
    version: 1,
    versionNonce: 5000 + seq * 193,
    isDeleted: false,
    boundElements: [],
    updated: now,
    link: null,
    locked: false,
  };
}

function rect(id, x, y, w, h, fill, stroke = "#1e1e1e", opts = {}) {
  elements.push(base("rectangle", id, x, y, w, h, {
    backgroundColor: fill,
    strokeColor: stroke,
    ...opts,
  }));
}

function text(id, x, y, w, h, value, size = 24, color = "#1e1e1e", align = "center", opts = {}) {
  const e = base("text", id, x, y, w, h, {
    strokeColor: color,
    backgroundColor: "transparent",
    strokeWidth: 1,
    roughness: 0,
    ...opts,
  });
  Object.assign(e, {
    fontSize: size,
    fontFamily: 1,
    text: value,
    rawText: value,
    originalText: value,
    textAlign: align,
    verticalAlign: "middle",
    containerId: null,
    autoResize: false,
    lineHeight: 1.25,
  });
  elements.push(e);
}

function arrow(id, x1, y1, x2, y2, color = "#1e1e1e", label = "") {
  const e = base("arrow", id, x1, y1, Math.abs(x2 - x1), Math.abs(y2 - y1), {
    strokeColor: color,
    backgroundColor: "transparent",
    roughness: 1,
  });
  Object.assign(e, {
    points: [[0, 0], [x2 - x1, y2 - y1]],
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: null,
    endArrowhead: "arrow",
    elbowed: false,
  });
  elements.push(e);
  if (label) text(`${id}-label`, (x1 + x2) / 2 - 75, (y1 + y2) / 2 - 28, 150, 26, label, 16, color);
}

function node(id, x, y, w, h, title, subtitle, fill, stroke) {
  rect(`${id}-box`, x, y, w, h, fill, stroke);
  text(`${id}-title`, x + 12, y + 14, w - 24, 34, title, 25, stroke);
  text(`${id}-sub`, x + 16, y + 54, w - 32, h - 66, subtitle, 17, "#343a40");
}

// Header
text("title", 70, 38, 1780, 58, "PostgreSQL 17 GiST Spatial Indexing at 500M Geo-Points", 38, "#1e1e1e");
text("subtitle", 160, 103, 1600, 34, "Reproduction, measured performance, and Geo-hash trade-off analysis", 22, "#495057");

// Environment and pipeline
text("pipeline-heading", 70, 165, 500, 36, "1. Reproducible pipeline", 27, "#1864ab", "left");
node("cloud", 75, 220, 270, 135, "Hetzner CPX42", "8 vCPU • 16 GB RAM\n320 GB SSD", "#e7f5ff", "#1864ab");
node("docker", 415, 220, 270, 135, "Docker Compose", "PostgreSQL 17.5 + PostGIS\npgAdmin 4 via SSH tunnel", "#e7f5ff", "#1864ab");
node("load", 755, 220, 270, 135, "Generate data", "500,000,000 points\nUniform lon/lat distribution", "#fff3bf", "#e67700");
node("baseline", 1095, 220, 270, 135, "Before GiST", "Parallel Seq Scan\n21.6–29.9 seconds", "#ffe3e3", "#c92a2a");
node("index", 1435, 220, 350, 135, "Build GiST index", "31 GB • 14m 10.698s\nThen rerun every query", "#d3f9d8", "#2b8a3e");
arrow("a-cloud-docker", 345, 287, 415, 287, "#1864ab");
arrow("a-docker-load", 685, 287, 755, 287, "#1864ab");
arrow("a-load-base", 1025, 287, 1095, 287, "#e67700");
arrow("a-base-index", 1365, 287, 1435, 287, "#2b8a3e");

// Dataset evidence
text("evidence-heading", 70, 402, 500, 36, "2. Scale evidence", 27, "#6741d9", "left");
const metrics = [
  ["500,000,000", "exact rows"],
  ["36 GB", "table heap"],
  ["10 GB", "primary key"],
  ["31 GB", "GiST index"],
  ["77 GB", "table + indexes"],
  ["25 min", "full pipeline"],
];
metrics.forEach((m, i) => {
  const x = 75 + i * 285;
  rect(`metric-${i}`, x, 455, 245, 105, "#f3f0ff", "#6741d9");
  text(`metric-${i}-v`, x + 10, 468, 225, 42, m[0], 27, "#5f3dc4");
  text(`metric-${i}-l`, x + 10, 515, 225, 28, m[1], 17, "#495057");
});

// Before / after table
text("perf-heading", 70, 610, 700, 36, "3. Nearby-places performance", 27, "#2b8a3e", "left");
rect("perf-panel", 75, 660, 1120, 385, "#f8f9fa", "#868e96", { roughness: 0 });
text("q-head", 105, 680, 290, 34, "Query", 20, "#343a40", "left");
text("b-head", 430, 680, 245, 34, "Before GiST", 20, "#c92a2a", "left");
text("a-head", 710, 680, 245, 34, "After GiST (cold)", 20, "#2b8a3e", "left");
text("p-head", 965, 680, 200, 34, "Plan", 20, "#1864ab", "left");
const rows = [
  ["NYC box", "21,820.542 ms", "63.938 ms", "Bitmap"],
  ["Circle", "22,121.710 ms", "0.093 ms", "Bitmap"],
  ["Top-100 K-NN", "29,897.233 ms", "0.321 ms", "K-NN scan"],
  ["Polygon COUNT", "21,644.234 ms", "3.798 ms", "Index only"],
  ["Polygon rows", "same predicate", "13.597 ms", "Bitmap"],
];
rows.forEach((r, i) => {
  const y = 735 + i * 57;
  if (i % 2 === 0) rect(`row-bg-${i}`, 92, y - 7, 1086, 49, "#f1f3f5", "transparent", { strokeWidth: 1, roughness: 0 });
  text(`r-${i}-q`, 105, y, 290, 30, r[0], 18, "#343a40", "left");
  text(`r-${i}-b`, 430, y, 245, 30, r[1], 18, "#c92a2a", "left");
  text(`r-${i}-a`, 710, y, 245, 30, r[2], 18, "#2b8a3e", "left");
  text(`r-${i}-p`, 965, y, 200, 30, r[3], 17, "#1864ab", "left");
});

// Interpretation
rect("why", 1250, 660, 535, 385, "#ebfbee", "#2b8a3e");
text("why-title", 1280, 682, 475, 36, "Why GiST wins", 25, "#2b8a3e");
text("why-body", 1290, 735, 455, 250,
  "BEFORE\nScan all 500M rows\nParallel workers reduce time, not I/O\n\nAFTER\nSpatial keys prune most rows\nBitmap scans fetch small candidate sets\nK-NN stops after the top 100\n\nRESULT\nSeconds become milliseconds",
  19, "#343a40", "left");

// Geohash comparison
text("geo-heading", 70, 1095, 800, 36, "4. Geo-hash extension: useful filter, not exact distance", 27, "#e67700", "left");
node("gh", 75, 1150, 520, 300, "Geo-hash + B-tree", "50M-row comparison\nIndex: 1,071 MB\n48,768 candidates → 108 true rows\nPrecision: 0.221%\nRecall: 100%\nOverfetch: 451.6×", "#fff3bf", "#e67700");
node("gist", 670, 1150, 520, 300, "GiST", "Comparison index: 3,181 MB\nNative spatial predicates\nExact containment + recheck\nOrdered nearest-neighbor scan\nTop-100 K-NN: 0.321 ms cold", "#d3f9d8", "#2b8a3e");
node("hybrid", 1265, 1150, 520, 300, "Best production design", "Geo-hash for partitioning, routing, caches\n+\nGiST for exact box/circle/polygon filters\nand final K-NN ranking", "#e7f5ff", "#1864ab");
arrow("gh-to-gist", 595, 1300, 670, 1300, "#495057", "compare");
arrow("gist-to-hybrid", 1190, 1300, 1265, 1300, "#495057", "combine");

// Boundary insight and conclusion
rect("boundary", 75, 1495, 835, 190, "#fff4e6", "#e67700");
text("boundary-title", 105, 1515, 775, 34, "Geo-hash boundary problem", 24, "#e67700");
text("boundary-body", 115, 1565, 755, 90,
  "877 / 1,000 point pairs only ~101 m apart crossed precision-7 cell boundaries.\nA single prefix can miss nearby places; neighboring cells and exact distance rechecks are required.",
  18, "#343a40", "left");

rect("learning", 950, 1495, 835, 190, "#e7f5ff", "#1864ab");
text("learning-title", 980, 1515, 775, 34, "What we learned", 24, "#1864ab");
text("learning-body", 990, 1565, 755, 90,
  "At 500M rows, correctness and access path matter more than raw parallelism.\nGiST directly solves nearby-place filtering and ranking; Geo-hash is strongest as a distributed routing key.",
  18, "#343a40", "left");

text("footer", 75, 1725, 1710, 32,
  "Evidence: Docker Compose • SQL 01–10 • captured EXPLAIN (ANALYZE, BUFFERS) transcripts • final 14-page PDF",
  18, "#495057");

const doc = {
  type: "excalidraw",
  version: 2,
  source: "https://excalidraw.com",
  elements,
  appState: {
    gridSize: null,
    gridStep: 5,
    gridModeEnabled: false,
    viewBackgroundColor: "#ffffff",
  },
  files: {},
};

const out = path.join(outDir, "postgres-gist-500m-summary.excalidraw");
fs.writeFileSync(out, JSON.stringify(doc, null, 2));
console.log(out);
