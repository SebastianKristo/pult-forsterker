/**
 * Electron (V8 «memory cage», Electron ≥ 21) forbyr eksterne buffere fra native kode. @ronomon/direct-io lager justerte
 * buffere med napi_create_external_buffer, og skriveprosessen krasjer da med «Assertion failed … get_aligned_buffer».
 * Vi skriver uten O_DIRECT/NO_BUFFERING (direct: false i writer.ts), så adressejustering trengs ikke: vanlige Buffer-er
 * holder. Lengden beholdes som et helt antall sektorer. Må importeres før etcher-sdk.
 */
// eslint-disable-next-line @typescript-eslint/no-var-requires
const directIo = require('@ronomon/direct-io') as { getAlignedBuffer: (size: number, alignment: number) => Buffer };
directIo.getAlignedBuffer = (size: number) => Buffer.alloc(size);
export {};
