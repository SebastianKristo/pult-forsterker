export interface Status { power: boolean; volume: number; mute: boolean; input: string; inputs?: string[]; preset?: number; name?: string; title?: string; artist?: string; [k: string]: unknown }
export class SkjoldFeil extends Error { status: number }
export class Skjold {
  constructor(vert?: string, opts?: { port?: number; base?: string; fetch?: typeof fetch });
  base: string;
  request<T = Status>(metode: string, sti: string, body?: unknown): Promise<T>;
  get<T = Status>(sti: string): Promise<T>;
  post<T = Status>(sti: string, body?: unknown): Promise<T>;
  status(): Promise<Status>;
  power(on?: boolean): Promise<Status>;
  toggle(): Promise<Status>;
  volume(volume?: number, opts?: { delta?: number }): Promise<Status>;
  mute(mute?: boolean): Promise<Status>;
  input(input: string): Promise<Status>;
  preset(n: number): Promise<Status>;
  play(url: string, ekstra?: { title?: string; artist?: string; image?: string; announce?: boolean; volume?: number }): Promise<Status>;
  transport(action: "play" | "pause" | "playpause" | "next" | "previous" | "stop"): Promise<Status>;
  events(opts?: { signal?: AbortSignal }): AsyncGenerator<Status>;
}
export default Skjold;
