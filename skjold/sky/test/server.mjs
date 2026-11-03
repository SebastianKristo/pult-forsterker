// Starter Workeren lokalt (Miniflare, DEV_INSECURE=1) og skriver adressen som én JSON-linje på stdout.
// Brukes av pi/tests/test_sky.py for å teste enhetsmodulen mot den ekte Workeren. Stopper når stdin lukkes.
import { lagMiniflare } from "./hjelp.mjs";

const mf = lagMiniflare({ host: "127.0.0.1", port: 0 });
const url = await mf.ready;
process.stdout.write(JSON.stringify({ url: url.toString().replace(/\/$/, "") }) + "\n");
process.stdin.resume();
process.stdin.on("end", async () => {
  await mf.dispose();
  process.exit(0);
});
