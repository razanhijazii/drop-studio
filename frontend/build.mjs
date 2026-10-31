// Build:  API_URL=https://your-api.onrender.com node build.mjs
// Dev:    node build.mjs --serve   (http://localhost:5173, API at http://localhost:8000)
import * as esbuild from "esbuild";
import { cpSync, mkdirSync, rmSync } from "node:fs";

const serve = process.argv.includes("--serve");
const apiUrl = (process.env.API_URL || "http://localhost:8000").replace(/\/$/, "");

rmSync("dist", { recursive: true, force: true });
mkdirSync("dist", { recursive: true });
cpSync("public", "dist", { recursive: true });

const options = {
  entryPoints: ["src/main.tsx"],
  bundle: true,
  outdir: "dist/assets",
  entryNames: "app",
  format: "esm",
  target: "es2020",
  jsx: "automatic",
  sourcemap: true,
  minify: !serve,
  loader: { ".css": "css" },
  define: {
    __API_URL__: JSON.stringify(apiUrl),
    "process.env.NODE_ENV": JSON.stringify(serve ? "development" : "production"),
  },
  logLevel: "info",
};

if (serve) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  const { port } = await ctx.serve({ servedir: "dist", port: 5173, fallback: "dist/index.html" });
  console.log(`Drop Studio running at http://localhost:${port}  (API: ${apiUrl})`);
} else {
  await esbuild.build(options);
}
