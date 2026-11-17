/** Merke for SUB/WAVE (bølgen) – integrasjonen har ingen egen bildefil. */

/** SUB/WAVE: en lydbølge i hvitt på stasjonens lilla. */
export function SubwaveMark({ size = '62%' }: { size?: string }) {
  return (
    <svg viewBox="0 0 24 24" style={`width:${size};height:${size};display:block`} fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M2 12c1.6-5 3.4-5 5 0s3.4 5 5 0 3.4-5 5 0 3.4 5 5 0" />
    </svg>
  );
}
