/** Merke for SUB/WAVE – integrasjonen har ingen egen bildefil i stor størrelse. */

/** SUB/WAVE: lys skive med svarte stråler rundt en rød-oransje kjerne (tegnet etter SUB/WAVE-logoen). */
export function SubwaveMark({ size = '78%' }: { size?: string }) {
  const n = 24, rays = [];
  for (let k = 0; k < n; k++) {
    const a = (k / n) * Math.PI * 2, w = Math.PI / n * 0.62;
    const p = (r: number, d: number) => `${(12 + r * Math.cos(a + d)).toFixed(3)} ${(12 + r * Math.sin(a + d)).toFixed(3)}`;
    rays.push(<path key={k} d={`M${p(4.9, -w * 0.55)} L${p(11.2, -w)} L${p(11.2, w)} L${p(4.9, w * 0.55)} Z`} fill="#141414" />);
  }
  return (
    <svg viewBox="0 0 24 24" style={`width:${size};height:${size};display:block`} aria-hidden="true">
      <circle cx="12" cy="12" r="11.9" fill="#f3ece0" />
      {rays}
      <circle cx="12" cy="12" r="4.6" fill="#dc4a28" />
    </svg>
  );
}
