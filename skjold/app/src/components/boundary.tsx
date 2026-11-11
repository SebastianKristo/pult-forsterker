// Feilgrense: en krasj i én side, hylle eller ett panel skal ikke fryse hele appen. Viser en liten melding med
// «Prøv igjen» i stedet, og resten (faner, minispiller, meny) virker som før. Nullstilles når `key` endres.
import { Component, type ComponentChildren } from 'preact';

export class Boundary extends Component<{ children?: ComponentChildren; liten?: boolean }, { feil: boolean }> {
  state = { feil: false };
  static getDerivedStateFromError(): { feil: boolean } { return { feil: true }; }
  componentDidCatch(e: unknown): void { try { console.error('Skjold: en del av siden krasjet', e); } catch { /* ignore */ } }
  render(): ComponentChildren {
    if (!this.state.feil) return this.props.children;
    if (this.props.liten) return null;   // en hylle på Hjem: bare skjul den
    return (
      <div role="alert" style="display:flex;flex-direction:column;gap:10px;align-items:flex-start;padding:18px;border-radius:14px;border:1px solid #2e2e30;background:#141415">
        <span style="font-size:15px;font-weight:600">Noe gikk galt her</span>
        <span style="font-size:13px;color:#8b8b86;line-height:1.5">Denne delen fikk et svar den ikke forsto. Resten av appen virker som vanlig.</span>
        <button onClick={() => this.setState({ feil: false })} style="height:36px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer">Prøv igjen</button>
      </div>
    );
  }
}
