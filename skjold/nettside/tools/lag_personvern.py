#!/usr/bin/env python3
"""Lager personvernsidene /personvern/ og /en/privacy/ fra malen i stotte/ og en/support/.

Kjør fra skjold/nettside: python3 tools/lag_personvern.py
"""
import re
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
OPPDATERT = ("27. november 2026", "27 November 2026")

CSS = """<style>
.pv{max-width:760px;margin:0 auto;padding:110px 22px 100px}
.pv h1{font-family:var(--sora);font-size:clamp(34px,5vw,52px);letter-spacing:-.02em;margin:10px 0 14px}
.pv .ingress{font-size:19px;line-height:1.6;color:var(--demp-l,#b9b6ad);margin:0 0 10px}
.pv .dato{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--gull,#d8b66a);text-transform:uppercase}
.pv-kort{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:34px 0 10px}
.pv-kort div{background:var(--kort,#141416);border:1px solid var(--linje,#26262a);border-radius:14px;padding:16px 18px}
.pv-kort b{display:block;font-family:var(--sora);font-size:15px;margin-bottom:4px}
.pv-kort span{font-size:14px;line-height:1.5;color:var(--demp-l,#b9b6ad)}
.pv h2{font-family:var(--sora);font-size:23px;margin:48px 0 12px;padding-top:22px;border-top:1px solid var(--linje,#26262a)}
.pv h3{font-family:var(--sora);font-size:17px;margin:24px 0 8px}
.pv p,.pv li{font-size:16px;line-height:1.7}
.pv ul{padding-left:20px;margin:8px 0 14px}
.pv li{margin:4px 0}
.pv table{width:100%;border-collapse:collapse;margin:12px 0 18px;font-size:15px}
.pv th,.pv td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid var(--linje,#26262a);line-height:1.5}
.pv th{font-family:var(--mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--demp-l,#b9b6ad);font-weight:500}
.pv a{color:var(--gull,#d8b66a)}
.pv code{font-family:var(--mono);font-size:.9em}
@media (max-width:560px){.pv table,.pv thead,.pv tbody,.pv tr,.pv th,.pv td{display:block}.pv thead{display:none}.pv td{border:0;padding:3px 0}.pv tr{border-bottom:1px solid var(--linje,#26262a);padding:10px 0}.pv td:first-child{font-weight:600}}
</style>"""

NB = f"""<main id="hoved"><article class="pv">
<div class="dato" data-reveal="0">Sist oppdatert {OPPDATERT[0]}</div>
<h1 data-reveal="40">Personvern</h1>
<p class="ingress" data-reveal="80">Skjold er laget for å virke lokalt i hjemmet ditt. Det meste blir aldri sendt noe sted. Her står hva som likevel lagres, hvor, hvorfor og hvordan du sletter det. Erklæringen gjelder appen Skjold Lab (iPhone, iPad og Apple Watch), Skjold-enhetene, skyen Skjold-hjem og nettsiden skjold-lab.com.</p>
<div class="pv-kort" data-reveal="120">
<div><b>Ingen sporing</b><span>Ingen reklame, ingen analyseverktøy og ingen deling med tredjeparter for markedsføring.</span></div>
<div><b>Lokalt først</b><span>Appen snakker med enhetene dine på det lokale nettet. Du trenger ingen konto.</span></div>
<div><b>Du bestemmer</b><span>Kontoen i Skjold-hjem er valgfri, og du kan slette den selv når som helst.</span></div>
</div>

<h2>Hvem er ansvarlig</h2>
<p>Behandlingsansvarlig er Skjold Lab ved Sebastian Kristo Jemtland, Norge. Spørsmål om personvern sendes til <a href="mailto:jemtlands@proton.me">jemtlands@proton.me</a>.</p>

<h2>Appen Skjold Lab</h2>
<p>Appen har ingen analyse-, reklame- eller krasjrapporteringsverktøy, og den sporer deg ikke på tvers av apper og nettsider. Uten innlogging i Skjold-hjem blir ingenting om deg sendt til Skjold Lab.</p>
<h3>Tillatelser</h3>
<table><thead><tr><th>Tillatelse</th><th>Brukes til</th></tr></thead><tbody>
<tr><td>Lokalt nettverk</td><td>Finne og styre Skjold-enhetene dine (Bonjour). Trafikken går direkte mellom telefonen og enheten.</td></tr>
<tr><td>Kamera</td><td>Lese QR-koden når du legger til en enhet eller blir med i et hjem. Bildene lagres ikke og sendes ikke noe sted.</td></tr>
<tr><td>Mikrofon</td><td>Romtilpasning (EQ): appen lytter til testtonen fra høyttaleren og regner ut justeringen på telefonen. Lyden tas ikke opp og sendes ikke noe sted.</td></tr>
<tr><td>NFC</td><td>Lese og skrive Skjold Spole-kassetter. Det som står på brikken, er en henvisning til musikk, ikke personopplysninger.</td></tr>
</tbody></table>
<h3>Tjenester appen kontakter</h3>
<ul>
<li><b>Skjold-enhetene dine</b> på det lokale nettet.</li>
<li><b>Musikkservere du legger inn selv</b> (Navidrome, Plex, Lyrion). Adresse, brukernavn og passord lagres bare på telefonen og sendes bare til den serveren.</li>
<li><b>Radio Browser</b> (radio-browser.info) når du søker etter radiostasjoner, og stasjonens egen server når du spiller. Søket sendes uten noe som identifiserer deg.</li>
<li><b>GitHub</b> for å se om det finnes nye versjoner av programvaren.</li>
<li><b>Skjold-hjem</b> (hjem.skjold-lab.com), bare hvis du logger inn.</li>
</ul>
<p>Disse tjenestene ser IP-adressen din, slik alle nettjenester gjør. Radio Browser, GitHub og radiostasjonene har egne personvernerklæringer.</p>

<h2>Skjold-enhetene</h2>
<p>S1, Node, Touch og de andre enhetene lagrer innstillingene, favorittene og lyttehistorikken lokalt. Talestyring på Skjold-enheter kjøres lokalt eller via Home Assistant, Homey eller Lyrion du selv har satt opp. Enhetene kontakter GitHub for oppdateringer. Er de med i et hjem i Skjold-hjem, melder de også fra om navn, produkt, versjon og lokal IP-adresse, slik at appen og nettsiden kan finne dem.</p>
<p>En enhet som ikke er med i et hjem, kan be om å bli funnet av et hjem på samme nett. Da lagres enhetens ID og lokale adresse i kort tid sammen med en kryptografisk hash av den offentlige IP-adressen, ikke selve adressen.</p>

<h2>Skjold-hjem (valgfri konto)</h2>
<p>Skjold-hjem lar deg styre enhetene utenfra, dele et hjem med familien og ta sikkerhetskopi. Vi lagrer:</p>
<table><thead><tr><th>Hva</th><th>Hvorfor</th><th>Hvor lenge</th></tr></thead><tbody>
<tr><td>E-postadresse</td><td>Innlogging (engangskode på e-post) og å identifisere kontoen</td><td>Til du sletter kontoen</td></tr>
<tr><td>Navn og profilbilde (valgfritt)</td><td>Vises for andre i hjemmet ditt</td><td>Til du endrer eller sletter det</td></tr>
<tr><td>Hjem, medlemmer og enheter</td><td>Å vite hvem som har tilgang til hvilke enheter</td><td>Til du sletter hjemmet eller kontoen</td></tr>
<tr><td>Totrinnsbekreftelse og passkeys</td><td>Sikre kontoen. Vi lagrer bare offentlige nøkler og hemmeligheten til kodeappen, aldri passord</td><td>Til du fjerner dem</td></tr>
<tr><td>Økter (innloggede enheter)</td><td>Holde deg innlogget. Informasjonskapselen <code>skjold_okt</code> varer i opptil 400 dager og fornyes når du bruker tjenesten</td><td>Til du logger ut, avslutter økten eller sletter kontoen</td></tr>
<tr><td>Sikkerhetslogg: tidspunkt, hendelse (for eksempel innlogging, ny passkey, endret profil), IP-adresse og omtrentlig sted (land og by)</td><td>Oppdage misbruk og innbrudd, og hjelpe deg om noe går galt</td><td>De nyeste 20 000 hendelsene for hele tjenesten beholdes. Eldre slettes fortløpende</td></tr>
</tbody></table>
<p>Behandlingsgrunnlaget er avtalen med deg (GDPR art. 6 nr. 1 b) for kontoen, og berettiget interesse i å sikre tjenesten (art. 6 nr. 1 f) for sikkerhetsloggen.</p>
<h3>Skjold Cloud</h3>
<p>Sikkerhetskopien av favoritter, rutiner og innstillinger krypteres på enheten før den sendes (ende-til-ende). Skyen ser bare navn på delen, versjon, størrelse og tidspunkt, aldri innholdet. Du kan slette den når som helst (se under).</p>
<h3>Delte kassetter og høyttalerprofiler</h3>
<p>Deler du en kassett, lagres listen kryptert, og nøkkelen står bare i delingskoden. Høyttalerprofiler i Skjold Sertifisert er anonyme. For å hindre misbruk lagres bare en hash av IP-adressen, ikke selve adressen.</p>

<h2>Hvem behandler dataene</h2>
<p>Skjold-hjem og nettsiden driftes hos <b>Cloudflare</b> (databehandler), som også står for innloggingen med e-postkode (Cloudflare Access). Data kan bli behandlet utenfor EØS. Overføringen er dekket av EUs standardavtaler og EU–US Data Privacy Framework. Vi selger aldri data og deler dem ikke med andre.</p>

<h2>Nettsiden skjold-lab.com</h2>
<p>Nettsiden bruker ingen informasjonskapsler til sporing og ingen analyseverktøy. Skriftene ligger på vår egen server. Cloudflare behandler IP-adresser og tekniske logger for å levere sidene og stoppe angrep.</p>

<h2>Slett dataene dine</h2>
<ul>
<li><b>Appen:</b> slett appen, så forsvinner alt den har lagret på telefonen.</li>
<li><b>Kontoen:</b> i Skjold-kontoen (fra appen eller på hjem.skjold-lab.com) under Data og personvern → Slett kontoen. Kontoen, profilen, passkeys, øktene, medlemskapene og Skjold Cloud slettes straks. Eier du et hjem, må du overføre det eller slette det først. Enhetene virker videre lokalt.</li>
<li><b>Skjold Cloud alene:</b> Data og personvern → Slett alt i Skjold Cloud.</li>
<li><b>Sikkerhetsloggen:</b> hendelsene forsvinner etter hvert som nye kommer inn. Vil du at de skal slettes med en gang, send en e-post.</li>
<li><b>Enhetene:</b> tilbakestill enheten fra innstillingene.</li>
</ul>

<h2>Rettighetene dine</h2>
<p>Du har rett til innsyn, retting, sletting, begrensning, dataportabilitet og til å protestere mot behandling. Send en e-post til <a href="mailto:jemtlands@proton.me">jemtlands@proton.me</a>, så svarer vi innen 30 dager. Mener du at vi behandler opplysninger i strid med regelverket, kan du klage til <a href="https://www.datatilsynet.no/">Datatilsynet</a>.</p>

<h2>Barn</h2>
<p>Skjold-hjem er ikke laget for barn under 13 år. Barn kan bruke enhetene og appen lokalt, uten konto.</p>

<h2>Endringer</h2>
<p>Endrer vi hvordan data behandles, oppdaterer vi denne siden og datoen øverst. Ved større endringer sier vi fra i appen.</p>
</article></main>"""

EN = f"""<main id="hoved"><article class="pv">
<div class="dato" data-reveal="0">Last updated {OPPDATERT[1]}</div>
<h1 data-reveal="40">Privacy</h1>
<p class="ingress" data-reveal="80">Skjold is built to work locally in your home. Most things are never sent anywhere. This page explains what is stored anyway, where, why and how to delete it. It covers the Skjold Lab app (iPhone, iPad and Apple Watch), the Skjold devices, the Skjold-hjem cloud and the website skjold-lab.com.</p>
<div class="pv-kort" data-reveal="120">
<div><b>No tracking</b><span>No ads, no analytics and no sharing with third parties for marketing.</span></div>
<div><b>Local first</b><span>The app talks to your devices on the local network. No account needed.</span></div>
<div><b>You decide</b><span>The Skjold-hjem account is optional, and you can delete it yourself at any time.</span></div>
</div>

<h2>Who is responsible</h2>
<p>The controller is Skjold Lab, Sebastian Kristo Jemtland, Norway. Send privacy questions to <a href="mailto:jemtlands@proton.me">jemtlands@proton.me</a>.</p>

<h2>The Skjold Lab app</h2>
<p>The app has no analytics, advertising or crash reporting SDKs, and it does not track you across apps and websites. Without signing in to Skjold-hjem, nothing about you is sent to Skjold Lab.</p>
<h3>Permissions</h3>
<table><thead><tr><th>Permission</th><th>Used for</th></tr></thead><tbody>
<tr><td>Local network</td><td>Finding and controlling your Skjold devices (Bonjour). Traffic goes directly between the phone and the device.</td></tr>
<tr><td>Camera</td><td>Reading the QR code when you add a device or join a home. Images are not stored or sent anywhere.</td></tr>
<tr><td>Microphone</td><td>Room correction (EQ): the app listens to the test tone from the speaker and calculates the adjustment on the phone. Audio is not recorded or sent anywhere.</td></tr>
<tr><td>NFC</td><td>Reading and writing Skjold Spole cassettes. The tag holds a reference to music, not personal data.</td></tr>
</tbody></table>
<h3>Services the app contacts</h3>
<ul>
<li><b>Your Skjold devices</b> on the local network.</li>
<li><b>Music servers you add yourself</b> (Navidrome, Plex, Lyrion). Address, username and password are stored only on the phone and sent only to that server.</li>
<li><b>Radio Browser</b> (radio-browser.info) when you search for radio stations, and the station's own server when you play. Searches are sent without anything that identifies you.</li>
<li><b>GitHub</b> to check for new software versions.</li>
<li><b>Skjold-hjem</b> (hjem.skjold-lab.com), only if you sign in.</li>
</ul>
<p>These services see your IP address, as all online services do. Radio Browser, GitHub and the radio stations have their own privacy policies.</p>

<h2>Skjold devices</h2>
<p>S1, Node, Touch and the other devices store settings, favourites and listening history locally. Voice control on Skjold devices runs locally or through the Home Assistant, Homey or Lyrion you have set up yourself. The devices contact GitHub for updates. If they are part of a home in Skjold-hjem, they also report name, product, version and local IP address, so the app and website can find them.</p>
<p>A device that is not part of a home can ask to be found by a home on the same network. Its ID and local address are then stored briefly together with a cryptographic hash of the public IP address, not the address itself.</p>

<h2>Skjold-hjem (optional account)</h2>
<p>Skjold-hjem lets you control your devices remotely, share a home with your family and back up settings. We store:</p>
<table><thead><tr><th>What</th><th>Why</th><th>How long</th></tr></thead><tbody>
<tr><td>Email address</td><td>Sign-in (one-time code by email) and identifying the account</td><td>Until you delete the account</td></tr>
<tr><td>Name and profile picture (optional)</td><td>Shown to other members of your home</td><td>Until you change or delete it</td></tr>
<tr><td>Homes, members and devices</td><td>Knowing who has access to which devices</td><td>Until you delete the home or the account</td></tr>
<tr><td>Two-step verification and passkeys</td><td>Securing the account. We store only public keys and the authenticator secret, never passwords</td><td>Until you remove them</td></tr>
<tr><td>Sessions (signed-in devices)</td><td>Keeping you signed in. The <code>skjold_okt</code> cookie lasts up to 400 days and is renewed while you use the service</td><td>Until you sign out, end the session or delete the account</td></tr>
<tr><td>Security log: time, event (for example sign-in, new passkey, profile change), IP address and approximate location (country and city)</td><td>Detecting abuse and break-ins, and helping you if something goes wrong</td><td>The latest 20,000 events for the whole service are kept. Older ones are deleted continuously</td></tr>
</tbody></table>
<p>The legal basis is our contract with you (GDPR Art. 6(1)(b)) for the account, and our legitimate interest in securing the service (Art. 6(1)(f)) for the security log.</p>
<h3>Skjold Cloud</h3>
<p>Backups of favourites, routines and settings are encrypted on the device before they are sent (end-to-end). The cloud only sees the part name, version, size and time, never the content. You can delete it at any time (see below).</p>
<h3>Shared cassettes and speaker profiles</h3>
<p>When you share a cassette, the list is stored encrypted, and the key exists only in the share code. Speaker profiles in Skjold Certified are anonymous. To prevent abuse, only a hash of the IP address is stored, not the address itself.</p>

<h2>Who processes the data</h2>
<p>Skjold-hjem and the website are hosted by <b>Cloudflare</b> (processor), which also handles sign-in with the email code (Cloudflare Access). Data may be processed outside the EEA. Transfers are covered by the EU Standard Contractual Clauses and the EU–US Data Privacy Framework. We never sell data and do not share it with anyone else.</p>

<h2>The website skjold-lab.com</h2>
<p>The website uses no tracking cookies and no analytics. Fonts are served from our own server. Cloudflare processes IP addresses and technical logs to deliver the pages and stop attacks.</p>

<h2>Delete your data</h2>
<ul>
<li><b>The app:</b> delete the app, and everything it stored on the phone is gone.</li>
<li><b>The account:</b> in your Skjold account (from the app or at hjem.skjold-lab.com) under Data og personvern (Data and privacy) → Slett kontoen (Delete account). The account, profile, passkeys, sessions, memberships and Skjold Cloud data are deleted immediately. If you own a home, transfer or delete it first. Your devices keep working locally.</li>
<li><b>Skjold Cloud only:</b> Data and privacy → delete everything in Skjold Cloud.</li>
<li><b>The security log:</b> events disappear as new ones come in. If you want them deleted right away, send an email.</li>
<li><b>Devices:</b> reset the device from its settings.</li>
</ul>

<h2>Your rights</h2>
<p>You have the right to access, rectification, erasure, restriction, data portability and to object to processing. Email <a href="mailto:jemtlands@proton.me">jemtlands@proton.me</a> and we will reply within 30 days. If you believe we process data unlawfully, you can complain to the Norwegian Data Protection Authority, <a href="https://www.datatilsynet.no/en/">Datatilsynet</a>, or your local authority.</p>

<h2>Children</h2>
<p>Skjold-hjem is not made for children under 13. Children can use the devices and the app locally, without an account.</p>

<h2>Changes</h2>
<p>If we change how data is processed, we update this page and the date at the top. For larger changes we will let you know in the app.</p>
</article></main>"""

SIDER = [
    dict(mal="stotte/index.html", ut="personvern/index.html", sti="/personvern/", gammel="/stotte/", main=NB,
         tittel="Personvern – Skjold Lab", besk="Hva Skjold-appen, enhetene og Skjold-hjem lagrer, hvorfor, og hvordan du sletter det. Ingen sporing og ingen analyseverktøy."),
    dict(mal="en/support/index.html", ut="en/privacy/index.html", sti="/en/privacy/", gammel="/en/support/", main=EN,
         tittel="Privacy – Skjold Lab", besk="What the Skjold app, devices and Skjold-hjem store, why, and how to delete it. No tracking and no analytics."),
]
NB_STI, EN_STI = "/personvern/", "/en/privacy/"


def lag(s):
    h = (ROT / s["mal"]).read_text(encoding="utf-8")
    h = re.sub(r"<title>[^<]*</title>", f"<title>{s['tittel']}</title>", h)
    h = re.sub(r'(<meta property="og:title" content=")[^"]*', r"\g<1>" + s["tittel"], h)
    h = re.sub(r'(<meta name="description" content=")[^"]*', r"\g<1>" + s["besk"], h)
    h = re.sub(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + s["besk"], h)
    h = re.sub(r'(<meta name="twitter:title" content=")[^"]*', r"\g<1>" + s["tittel"], h)
    h = re.sub(r'(<meta name="twitter:description" content=")[^"]*', r"\g<1>" + s["besk"], h)
    # lenker til siden selv og språkversjonene
    h = h.replace('href="https://skjold-lab.com/stotte/"', f'href="https://skjold-lab.com{NB_STI}"')
    h = h.replace('href="https://skjold-lab.com/en/support/"', f'href="https://skjold-lab.com{EN_STI}"')
    h = h.replace('content="https://skjold-lab.com' + s["gammel"] + '"', 'content="https://skjold-lab.com' + s["sti"] + '"')
    h = h.replace('<a href="/stotte/" lang="nb"', f'<a href="{NB_STI}" lang="nb"').replace('<a href="/en/support/" lang="en"', f'<a href="{EN_STI}" lang="en"')
    h = h.replace(' aria-current="page"', "")
    h = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", h, flags=re.S)
    h = h.replace("</head>", CSS + "\n</head>", 1)
    h = re.sub(r'<main id="hoved">.*?</main>', lambda _: s["main"], h, flags=re.S)
    ut = ROT / s["ut"]
    ut.parent.mkdir(parents=True, exist_ok=True)
    ut.write_text(h, encoding="utf-8")
    print("skrev", ut.relative_to(ROT))


if __name__ == "__main__":
    for s in SIDER:
        lag(s)
