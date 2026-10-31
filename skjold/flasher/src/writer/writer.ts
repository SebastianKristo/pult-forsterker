/**
 * Skriveprosessen. Kjøres som egen prosess (Electron-binæren med ELECTRON_RUN_AS_NODE=1), med administratorrettigheter
 * på macOS/Windows (sudo-prompt) og som vanlig bruker på Linux etter at hovedprosessen har gitt brukeren eierskap til
 * blokkenheten via pkexec. Rapporterer fremdrift som JSON-linjer over en lokal TCP-socket tilbake til GUI-et.
 *
 *   writer.js --job <fil.json>      { image, device, port, token }
 */
import './patch-direct-io';   // må komme før etcher-sdk
import { promises as fsp } from 'fs';
import net from 'net';
import * as drivelist from 'drivelist';
import { sourceDestination, multiWrite } from 'etcher-sdk';
import { isSafeTarget } from '../shared/drivefilter';
import type { WriterJob, WriterMessage } from '../shared/types';

async function main(): Promise<void> {
  const i = process.argv.indexOf('--job');
  if (i < 0) throw new Error('mangler --job');
  const jobFile = process.argv[i + 1];
  const job = JSON.parse(await fsp.readFile(jobFile, 'utf8')) as WriterJob;
  await fsp.rm(jobFile, { force: true }).catch(() => undefined);

  const sock = net.connect(job.port, '127.0.0.1');
  await new Promise<void>((res, rej) => { sock.once('connect', res); sock.once('error', rej); });
  const send = (m: WriterMessage) => sock.write(JSON.stringify(m) + '\n');
  send({ type: 'hello', token: job.token });

  try {
    // Finn disken på nytt og sjekk den igjen her, med forhøyede rettigheter – aldri systemdisker.
    const drive = (await drivelist.list()).find(d => d.device === job.device);
    if (!drive) throw new Error(`Fant ikke ${job.device}. Er kortet tatt ut?`);
    if (!isSafeTarget(drive)) throw new Error(`${job.device} er ikke en flyttbar disk – avbryter.`);

    const source = new sourceDestination.File({ path: job.image });
    const dest = new sourceDestination.BlockDevice({
      drive, write: true, direct: false,   // uten O_DIRECT/NO_BUFFERING – se patch-direct-io.ts
      unmountOnSuccess: process.platform !== 'linux', // på Linux er partisjonene avmontert av pkexec-trinnet
    });
    let last = 0;
    const { failures } = await multiWrite.pipeSourceToDestinations({
      source, destinations: [dest], verify: true, numBuffers: 32,
      onFail: () => undefined,
      onProgress: p => {
        const now = Date.now();
        if (now - last < 150 && (p.percentage ?? 0) < 100) return;
        last = now;
        send({ type: 'progress', phase: p.type === 'verifying' ? 'verifying' : 'flashing', percent: p.percentage ?? 0,
          bytes: p.position, total: p.size, speed: p.speed, eta: p.eta });
      },
    });
    const err = [...failures.values()][0];
    if (err) throw err;
    send({ type: 'done' });
  } catch (e) {
    send({ type: 'error', message: e instanceof Error ? e.message : String(e) });
  } finally {
    await new Promise<void>(res => sock.end(res));
  }
}

main().then(() => process.exit(0), e => { console.error(e); process.exit(1); });
