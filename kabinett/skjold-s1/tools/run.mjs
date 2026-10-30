// Kjører Skjold S1-generatorene lokalt (uten nett): node run.mjs <mappe-med-revb_features.js> [print|sheet|cnc|all]
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
const dir = path.resolve(process.argv[2]); const what = process.argv[3] || 'all';
const { REVB } = await import(pathToFileURL(path.join(dir, 'revb_features.js')).href);
const saveFile = async (p, d) => { if (d instanceof Blob) d = Buffer.from(await d.arrayBuffer()); const f = path.join(dir, p); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, d); console.log('skrev', p, (d.length / 1024).toFixed(0) + ' kB'); };
const log = console.log;
const here = path.dirname(fileURLToPath(import.meta.url));
const local = (src) => src
  .replace("await import('https://esm.sh/manifold-3d@3.0.0')", `await import('${pathToFileURL(path.join(here, 'node_modules/manifold-3d/manifold.js')).href}')`)
  .replace("{locateFile:()=> 'https://cdn.jsdelivr.net/npm/manifold-3d@3.0.0/manifold.wasm'}", `{locateFile:()=> '${path.join(here, 'node_modules/manifold-3d/manifold.wasm')}'}`)
  .replace("await import('https://esm.sh/three@0.170.0/examples/jsm/loaders/FontLoader.js')", `await import('${pathToFileURL(path.join(here, 'node_modules/three/examples/jsm/loaders/FontLoader.js')).href}')`)
  .replace("await import('https://esm.sh/fflate@0.8.2')", `await import('${pathToFileURL(path.join(here, 'node_modules/fflate/esm/browser.js')).href}')`)
  .replace("await (await fetch('https://unpkg.com/three@0.170.0/examples/fonts/helvetiker_bold.typeface.json')).json()", `JSON.parse(${JSON.stringify(fs.readFileSync(path.join(here, 'node_modules/three/examples/fonts/helvetiker_bold.typeface.json'), 'utf8'))})`);
const withLib = (src) => src.replace("log(Object.keys(out).length+' filer');\n})();", "log(Object.keys(out).length+' filer'); return {StepDoc,fpoly,rrect,rev,circ,hole,fr,FZ,FF,FB,FL,FRt,FY,DXF};\n})();");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const run = (file, extra = {}) => new Function('REVB', 'saveFile', 'log', ...Object.keys(extra), withLib(local(fs.readFileSync(path.join(dir, 'cad', file), 'utf8'))))(REVB, saveFile, log, ...Object.values(extra));
process.chdir(dir);
if (what === 'cnc' || what === 'all' || what === 'sheet') { const lib = await run('generate.js'); if (what === 'sheet' || what === 'all') await run('generate_sheet_round.js', { LIB: lib }); }
if (what === 'print' || what === 'all') await run('generate_print.js');
