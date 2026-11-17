/** Merker for integrasjoner uten egen bildefil: Homey (fargehjulet fra app-ikonet) og SUB/WAVE (bølgen). */

/** Homey: fire buer rundt en sirkel, tegnet etter Homey-ikonet (strektegning fra Arcticons, CC BY-SA 4.0), i farger. */
export function HomeyMark({ size = '70%' }: { size?: string }) {
  const arc = (d: string, c: string) => <path d={d} fill="none" stroke={c} stroke-width="4.2" stroke-linecap="round" />;
  return (
    <svg viewBox="0 0 48 48" style={`width:${size};height:${size};display:block`} aria-hidden="true">
      {arc('M32.72 32.72c7.203-7.202 7.203-18.88 0-26.083a18.4 18.4 0 0 0-5.846-3.946', '#ff3f6c')}
      {arc('M15.28 32.72c7.202 7.203 18.88 7.203 26.083 0a18.4 18.4 0 0 0 3.946-5.846', '#ffb300')}
      {arc('M15.28 15.28c-7.203 7.202-7.203 18.88 0 26.083a18.4 18.4 0 0 0 5.846 3.946', '#21c27a')}
      {arc('M32.72 15.28c-7.202-7.203-18.88-7.203-26.083 0a18.4 18.4 0 0 0-3.946 5.846', '#2f8cff')}
      <circle cx="24" cy="24" r="8.5" fill="#1d1d1f" />
    </svg>
  );
}

/** SUB/WAVE: en lydbølge i hvitt på stasjonens lilla. */
export function SubwaveMark({ size = '62%' }: { size?: string }) {
  return (
    <svg viewBox="0 0 24 24" style={`width:${size};height:${size};display:block`} fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M2 12c1.6-5 3.4-5 5 0s3.4 5 5 0 3.4-5 5 0 3.4 5 5 0" />
    </svg>
  );
}
