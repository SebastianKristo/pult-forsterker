// Skjold Dokk – ladestasjon for Skjold Fjernkontroll. Parametrisk OpenSCAD.
// Fjernkontrollen står i ca. 65° med baksiden mot ryggen og halen på en hylle. En magnetisk pogo-kontakt (2 pinner,
// handelen med fjærpinner i ryggen, hunndelen flatt i fjernkontrollens bunn) gir 5 V til laderen. USB-C bak.
// Toppen (vugga) printes i Bone White, sokkelen i mørk PETG/PLA med en gullstripe rundt. Ingen støtte.
// Lisens: CC BY-NC-SA 4.0.
//
// Koordinater: X tvers (0 = midten), Y fra fronten bakover, Z opp (0 = bordet).
// Fjernkontrollens egne koordinater (x tvers, y fra halen, z fra baksiden) legges inn med fk_plass().
// part: vugge | sokkel | gull | lokk | pogo_han | samlet | med_fjernkontroll | profil | sokkel_topp | sokkel_bunn | led_propp
//       ir_deler | ir_inni (med -D ir=true: IR-dokka, se «IR i dokka» under)
part = "samlet";
variant = "kort";                // kort | full (bare for bildene: dokka er lik for begge)
farge = "bone";                  // bone | mork
// stil på vugga (sokkelen er lik for begge, så en printet sokkel passer):
//   tvilling – lav pute foran som holder halen, og to slanke ribber bak som bærer fjernkontrollen (luft imellom)
//   skaal    – den første utgaven: skål foran og én bred finne bak
//   klem     – en avrundet skål som klemmer om sidene på fjernkontrollen et godt stykke opp, og glir inn i ryggen øverst
stil = "klem";

// ---------- fjernkontrollen (samme som skjold_fjernkontroll.scad) ----------
FW = 55; FH = 13.5;
FL = variant == "kort" ? 202.5 : 245.5;
hodeD = 4.3;                     // skruehodene i bunnen (hale: x 4,9 og 50,1, y 8) – nøklene i ryggen går inn her
SKRUE_HALE = [[4.9, 8], [FW - 4.9, 8]];

// ---------- pogo (samme som i skjold_fjernkontroll.scad – mål din) ----------
POGO_L = 21; POGO_KROPP = 15; POGO_B = 6; POGO_HM = 4.5; POGO_PINNE = 0.9; POGO_ORE_T = 1.2;
POGO_HULL = 1.8; POGO_HULL_A = 18; POGO_DELING = 2.8; POGO_ORE = true;
POGO_X = 40; POGO_Y = 43.5;      // hunndelens senter i fjernkontrollen

// ---------- dokka ----------
A = 65;                          // vinkel mot bordet
kl = 0.4;                        // klaring til sidene
rygg_t = 8;                      // ryggens tykkelse under fjernkontrollen
rygg_l = 78;                     // ryggens lengde langs fjernkontrollen
hylle_t = 6;                     // hyllens tykkelse under halen
leppe_h = 4;                     // leppa foran halen (dekker ikke SKJOLD-logoen, som starter 5,3 mm opp)
leppe_t = 3;
vegg = 3;                        // sidevangene
vange_h = 9;                     // vangene står så høyt opp fra ryggen
vange_l = 40;
VB = FW + 2*kl + 2*vegg;         // vuggas bredde
// sokkel
SB = 80; SY0 = -28; SY1 = 72;    // bredde, front og bakkant
SH = 12; SR = 16; SF = 4;        // høyde, hjørneradius, avrunding av toppkanten
gull_inn = 5.2; gull_b = 1.2; gull_d = 0.6;   // gullstripa rundt toppen (på den flate toppen, innenfor avrundingen)
// form på vugga (bare utsiden – alt fjernkontrollen berører er uendret)
rund = 5;                        // avrunding i sideprofilet (ryggens topp, leppa foran)
fas = 1.2;                       // myk 45°-fas på alle kanter (printes uten støtte)
plan_r = 9;                      // hjørneradius sett ovenfra
bak_y = 52;                      // finnen skråner ned til hit bak på sokkelen
finne_b = 36;                    // den smale ryggen («finnen») bak – pogo-kontakten sitter i den
skaal_l = 44;                    // skåla foran (full bredde, med hylle, leppe og vanger) langs fjernkontrollen
skaal_bak = 34;                  // skåla skråner ned til hit
// ---------- IR i dokka (bare med delt sokkel: delene legges inn nedenfra) ----------
// Sokkelen får en lomme for et ESP32-C3 SuperMini ved siden av USB-C-brikken (5 V fra samme brikke), to 5 mm
// IR-lysdioder foran (vippet opp mot TV-veggen og litt utover), en tredje bak eller på høyre side (til en boks bak
// TV-en eller i en hylle ved siden av), og et vindu for en VS1838B-mottaker (lære koder rett på dokka).
// Lysdiodene står i gjennomgående hull med fas: kuppelen ligger 0,3 mm inne i fronten, og flensen hviler mot et
// trinn innvendig. Fastvare: esphome/skjold-dokk.yaml.
ir = false;
ir_tredje = "bak";               // tredje IR-lysdiode: "bak" | "side" (høyre) | "ingen"
ir_mottaker = true;              // vindu og lomme for VS1838B
ir_X = 13;                       // de to fremre lysdiodene står ±ir_X fra midten
ir_z = 6.6;                      // høyden på hullsenteret i ytterflaten
ir_vinkel = 12;                  // vippet opp (grader)
ir_spre = 8;                     // vridd utover, hver sin vei (grader), for bredere kjegle
ir_d = 5.1;                      // hullet til 5 mm lysdiode (TSAL6200 eller vanlig 940 nm)
ir_fas = 0.7;                    // fas ytterst i hullet
ir_l = 8.6;                      // lysdiodens lengde fra flensen til tuppen (TSAL6200: 8,6)
ir_inne = 0.3;                   // kuppelen ligger så langt inne
ir_flens = 6.4;                  // trinnet innvendig (flensen er 5,8–6,0)
ir_kam = [36, 8.4, 8.0];         // kammeret bak de fremre lysdiodene: bredde, fra fronten, dybde (transistor og motstander)
mott = [9.4, 5.8, 7.4];          // VS1838B liggende på siden (b × d × h, kuppelen fram) – mål din
mott_vindu = 4.4;                // vinduet foran kuppelen
c3 = [18.0, 22.5, 3.6];          // ESP32-C3 SuperMini: b × l × tykkelse med komponenter (USB-C på kortenden)
c3_X = -18; c3_Y = 50.5;         // senter i sokkelen, USB-enden bakover (mot USB-C-brikken)
c3_lys = [-6, 9];                // den blå lysdioden (GPIO8) i forhold til kortets senter – lyslederen står over den
lysleder_d = 1.9;                // hull for en bit klar filament (1,75 mm) opp til toppen
ir_bak_X = 17;                   // tredje lysdiode bak (X), eller …
ir_side_Y = 26;                  // … på høyre side (Y)
// vekt og føtter
vekt = ir ? [36, 23, 7] : [48, 30, 7];   // lomme foran for stålkuler eller skiver (ca. 60–90 g, med IR ca. 45 g)
vekt_Y = ir ? 2.5 : -7;          // lommens senter (Y); med IR flyttes den bakover og krymper (IR-kammeret står foran)
led_X = 31;                      // lysdioden foran til høyre
fot_d = 10; fot_h = 1.0;         // gummiføtter
// USB-C-brikke (vanlig 6-pinners «Type-C breakout» med 5,1 kΩ på CC), bakerst
usb_kort = [12.2, 14.5, 1.6];    // b × d × t (kontakten mot bakkanten)
usb_k = [9.0, 7.4, 3.3];         // kontakten (b × d × h), stikker 0,6 mm ut over kortet
usb_X = 0;
led_d = 3.1;                     // valgfri lysdiode foran (3 mm)


hb = SH + hylle_t*sin(A) + rygg_t*cos(A);   // hjørnet mellom hylla og ryggen (z)
// fjernkontrollens koordinater → dokka
module fk_plass() { translate([0, 0, hb]) rotate([A, 0, 0]) translate([-FW/2, 0, 0]) children(); }
function fk(p) = [p[0] - FW/2, p[1]*cos(A) - p[2]*sin(A), hb + p[1]*sin(A) + p[2]*cos(A)];

module rrect(b, d, r) { offset(r) offset(-r) square([b, d]); }
module sokkel_2d(o = 0) { translate([-SB/2 + o, SY0 + o]) rrect(SB - 2*o, SY1 - SY0 - 2*o, SR - o); }

// vugga i fjernkontrollens koordinater (før plassering)
module vugge_lokal() {
  translate([-VB/2 + FW/2, -hylle_t, -rygg_t]) cube([VB, rygg_l + hylle_t, rygg_t]);                     // ryggen
  translate([-VB/2 + FW/2, -hylle_t, -rygg_t]) cube([VB, hylle_t, rygg_t + FH + kl + leppe_t]);          // hylla
  translate([-VB/2 + FW/2, 0, FH + kl]) cube([VB, leppe_h, leppe_t]);                                  // leppa
}
module vanger_lokal() {
  for (s = [0, 1]) translate([s ? FW + kl : -kl - vegg, 0, -0.01]) hull() {
    cube([vegg, vange_l, 0.01]);
    cube([vegg, vange_l - vange_h, vange_h]);
  }
}
module fk_rom() {                // plassen fjernkontrollen tar (pluss klaring til sidene)
  translate([-kl, 0, 0]) cube([FW + 2*kl, 400, FH + kl]);
  translate([-kl, leppe_h, 0]) cube([FW + 2*kl, 400, 200]);
}
module pogo_han_lokal() {        // handelen: flaten i z = 0, pinnene stikker POGO_PINNE opp
  translate([POGO_X, POGO_Y, 0]) {
    color([0.12, 0.12, 0.13]) difference() {
      union() {
        translate([0, 0, -POGO_HM/2]) cube([POGO_B, POGO_KROPP, POGO_HM], center = true);
        if (POGO_ORE) translate([0, 0, -POGO_HM]) linear_extrude(POGO_ORE_T) pogo_2d();
      }
      if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, -10]) cylinder(d = POGO_HULL, h = 20, $fn = 16);
    }
    color([0.85, 0.7, 0.35]) for (s = [-1, 1]) translate([0, s * POGO_DELING/2, -0.5]) cylinder(d = 1.2, h = 0.5 + POGO_PINNE, $fn = 16);
  }
}
module pogo_2d(o = 0) {
  if (POGO_ORE) hull() for (s = [-1, 1]) translate([0, s * (POGO_L/2 - POGO_B/2)]) circle(d = POGO_B + 2*o, $fn = 32);
  else square([POGO_B + 2*o, POGO_KROPP + 2*o], center = true);
}
module pogo_lomme_lokal() {      // lommen i ryggen: kroppen ned, ørene nederst (skrus fra undersiden av lomma)
  translate([POGO_X, POGO_Y, 0]) {
    translate([0, 0, -POGO_HM - 0.01]) linear_extrude(POGO_HM + 1) offset(0.12) square([POGO_B, POGO_KROPP], center = true);
    if (POGO_ORE) translate([0, 0, -POGO_HM - 0.01]) linear_extrude(POGO_ORE_T + 0.02) pogo_2d(0.2);
    if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, -POGO_HM - 2.6]) cylinder(d = 1.3, h = 3, $fn = 12);
  }
}
module nokler_lokal() {          // to knotter som går inn i skruehodene i halen: dokka kan bare tas én vei
  for (p = SKRUE_HALE) translate([p[0], p[1], -0.01]) cylinder(d1 = hodeD - 0.8, d2 = hodeD - 1.6, h = 0.8, $fn = 32);
}
// ledningskanal fra pogo-lomma ned til sokkelen (loddes på handelens pinner bakfra)
pogo_bunn = fk([POGO_X, POGO_Y, -POGO_HM]);
kanal_X = pogo_bunn[0]; kanal_Y = pogo_bunn[1];

// Ytterformen: sideprofilet (Y–Z) gjennom hjørnene på ryggen, hylla og leppa, ned til sokkelen og skrått bakover,
// avrundet; snittet med planformen (avrundet rektangel) og en myk fas rundt. Konveks, så minkowski går fort.
function ppkt(p) = [fk(p)[1], fk(p)[2]];
function profil(L) = [ppkt([0, -hylle_t, -rygg_t]), ppkt([0, L, -rygg_t]), ppkt([0, L, 0]),
                      ppkt([0, -hylle_t, FH + kl + leppe_t]), ppkt([0, leppe_h, FH + kl + leppe_t])];
prof_y0 = min([for (p = profil(rygg_l)) p[0]]);
module profil2d(L, y1, o = 0) {
  offset(r = rund - o) offset(delta = -rund) hull() {
    polygon(profil(L));
    translate([prof_y0, SH - 6]) square([y1 - prof_y0, 6]);
  }
}
module myk(b, L, y1, r) {        // konveks del: sideprofil × planform, med myk 45°-fas rundt
  minkowski() {
    intersection() {
      rotate([90, 0, 90]) linear_extrude(b - 2*fas, center = true) profil2d(L, y1, fas);
      translate([0, 0, -10]) linear_extrude(400) translate([-b/2 + fas, prof_y0 + fas]) rrect(b - 2*fas, y1 - prof_y0 - 2*fas, r - fas);
    }
    union() { cylinder(r1 = fas, r2 = 0, h = fas, $fn = 16); mirror([0, 0, 1]) cylinder(r1 = fas, r2 = 0, h = fas, $fn = 16); }
  }
}
// Ytterformen: en lav skål i full bredde foran (holder halen) og en smal, avrundet finne bak som bærer ryggen.
module ytre() {
  myk(VB, skaal_l, skaal_bak, plan_r);
  myk(finne_b, rygg_l, bak_y, finne_b/2 - 2);
}
// Tvilling: en lav, bred pute foran (hylla, leppa, vangene og nøklene) og to slanke, avrundede ribber bak som bærer
// fjernkontrollens bakside. Den høyre ribba har pogo-kontakten og ledningskanalen; mellom ribbene er det luft.
pute_l = 24;                     // puta langs fjernkontrollen
pute_bak = 26;                   // puta skråner ned til hit på sokkelen
ribbe_b = 14;                    // ribbenes bredde
ribbe_x = POGO_X - FW/2;         // ribbenes senter (±), den høyre midt over pogo-kontakten
module ytre_tvilling() {
  myk(VB, pute_l, pute_bak, plan_r);
  for (s = [-1, 1]) translate([s * ribbe_x, 0, 0]) myk(ribbe_b, rygg_l, bak_y, ribbe_b/2 - 1);
}
// Klem: et avrundet skall i fjernkontrollens koordinater. Tverrsnittet er en U med rund rygg (R = klemR) og
// vinger som går klem_h opp langs sidene (under forsiden, så tastene er fri). Vingene er fulle til klem_y og glir
// så mykt inn i ryggen fram til rygg_l. Under skallet står puta foran og de to ribbene (som i tvilling).
klem_v = 2.6;                     // vingenes tykkelse (skallet blir litt smalere enn puta, innenfor fasen)
klem_h = 11;                      // vingene står så høyt opp fra fjernkontrollens bakside (forsiden er i FH = 13,5)
klem_y = 34;                      // vingene er fulle hit, så glir de ned i ryggen
klemR = 12;                       // rund rygg i tverrsnittet
module klem_tverr2d() {           // tverrsnitt (x, z) i fjernkontrollens koordinater
  x0 = -kl - klem_v; x1 = FW + kl + klem_v; z0 = -rygg_t;
  hull() {
    for (x = [x0 + klemR, x1 - klemR]) translate([x, z0 + klemR]) circle(r = klemR, $fn = 96);
    for (x = [x0 + klem_v/2, x1 - klem_v/2]) translate([x, klem_h - klem_v/2]) circle(d = klem_v, $fn = 32);
  }
}
module klem_side2d() {            // sideprofil (y, z): fulle vinger fram til klem_y, så en myk bue ned i ryggen
  hull() {
    translate([-hylle_t, -rygg_t]) square([klem_y + hylle_t, klem_h + rygg_t]);
    translate([rygg_l - rygg_t, -rygg_t + 0.01]) intersection() { circle(r = rygg_t, $fn = 64); translate([-rygg_t, 0]) square(2 * rygg_t); }
  }
}
module klem_lokal() {
  intersection() {
    rotate([90, 0, 0]) translate([0, 0, -400]) linear_extrude(800) klem_tverr2d();                 // (x, z) langs y
    rotate([90, 0, 90]) translate([0, 0, -200]) linear_extrude(400) klem_side2d();                // (y, z) langs x
  }
}
// Innføring (klem): fjernkontrollen skal finne plassen sin selv og kunne løftes ut med én hånd. Vingenes innsider vider
// seg ut øverst (trakt), innerkantene på vingene og leppa er avfaset, så ingenting hekter seg.
trakt = 2.2;                      // så mye vingene vider seg ut mot toppen (per side)
trakt_y0 = klem_y - 12;           // trakten starter her (under er setet med vanlig klaring)
// Lading med kabel: spor i hylla for en vinklet (90°) USB-C-plugg i halen. Sporet er åpent mot fronten og til høyre,
// så pluggen settes i før fjernkontrollen settes ned, og kabelen går ut til høyre. Pogo-lomma er der fortsatt.
usb_spor = false;
usb_x = 27.5; usb_z = 4.7;        // USB-C i halen (Hullkort: midt på, 4,7 mm over undersiden)
usb_dybde = 9.5;                  // plass til den vinklede pluggen under halen
module usb_spor_lokal() {   // enden oppe skrår 25° (ellers henger leppa og vingen over sporet)
  z0 = usb_z - 4.2; b = FW + 30 - (usb_x - 7.5);
  hull() {
    translate([usb_x - 7.5, -usb_dybde, z0]) cube([b, usb_dybde + 0.5, 0.01]);
    translate([usb_x - 7.5, -usb_dybde, 60]) cube([b, usb_dybde + 0.5 + (60 - z0) * tan(25), 0.01]);
  }
}
module innforing_lokal() {
  for (s = [0, 1]) {
    x = s ? FW + kl : -kl; u = s ? 1 : -1;           // u peker utover
    // trakt: innsiden går fra x ved trakt_y0 til x + u·trakt ved rygg_l
    translate([0, 0, 0.3]) linear_extrude(klem_h + 2)
      polygon([[x - u * 2, trakt_y0], [x, trakt_y0], [x + u * trakt, rygg_l + 2], [x - u * 2, rygg_l + 2]]);
    // fas på innerkanten øverst langs hele vingen
    hull() {   // fasen vokser jevnt inn fra like over leppa (ingen trapp som henger over)
      rotate([90, 0, 0]) translate([0, 0, -rygg_l - 5]) linear_extrude(rygg_l + 5 - (leppe_h + 10))
        polygon([[x - u * 0.01, klem_h - 1.8], [x - u * 0.01, klem_h + 2], [x + u * 2.6, klem_h + 2]]);
      translate([x - u * 0.01, leppe_h + 2, klem_h + 1.9]) cube(0.01, center = true);
    }
  }
  // fas under leppa foran (forsiden glir forbi den når fjernkontrollen settes ned)
  translate([-kl, 0, 0]) rotate([90, 0, 90]) linear_extrude(FW + 2 * kl)   // bare over fjernkontrollens bredde
    polygon([[leppe_h + 0.01, FH + kl - 0.01], [leppe_h - 1.6, FH + kl - 0.01], [leppe_h + 0.01, FH + kl + 1.6]]);
}
module ytre_klem() {
  myk(VB, pute_l, pute_bak, plan_r);
  for (s = [-1, 1]) translate([s * ribbe_x, 0, 0]) myk(ribbe_b, rygg_l - 4, bak_y, ribbe_b/2 - 1);
  fk_plass() klem_lokal();
}
module vanger_myke(vl = vange_l) {   // vangene med avrundet toppkant, i fjernkontrollens koordinater
  for (s = [0, 1]) translate([s ? FW + kl : -kl - vegg + 0.05, 0, -0.01]) hull() {   // 0,05 mm inn: ikke i samme plan som siden
    cube([vegg - 0.05, vl, 0.01]);
    translate([vegg/2, 0, 0]) rotate([-90, 0, 0]) cylinder(d = vegg, h = vl - vange_h - 1.5, $fn = 24);
    translate([vegg/2, 0, vange_h - vegg/2]) rotate([-90, 0, 0]) cylinder(d = vegg, h = vl - vange_h - 1.5, $fn = 24);
  }
}
module vugge() {
  difference() {
    union() {
      if (stil == "klem") ytre_klem(); else if (stil == "tvilling") ytre_tvilling(); else ytre();
      fk_plass() { if (stil != "klem") vanger_myke(stil == "tvilling" ? pute_l - 2 : vange_l); nokler_lokal(); }
    }
    fk_plass() { fk_rom(); pogo_lomme_lokal(); if (stil == "klem") innforing_lokal(); if (usb_spor) usb_spor_lokal(); }
    translate([0, 0, -1]) linear_extrude(SH + 1) square([400, 400], center = true);   // står på sokkelen
    translate([kanal_X, kanal_Y, SH - 1]) cylinder(d = 4, h = pogo_bunn[2] - SH + 1.5, $fn = 20);   // ledninger
    for (x = [-20, 20]) translate([x, 8, SH - 1]) cylinder(d = 4.3, h = 5, $fn = 24);                  // tapper
  }
}
module sokkel() {
  difference() {
    union() {
      hull() {   // rund toppkant (kvart sirkel, R = SF), loddrett side og 0,4 mm fas nederst mot elefantfot
        translate([0, 0, 0.4]) linear_extrude(SH - SF - 0.4) sokkel_2d();
        linear_extrude(0.4) sokkel_2d(0.4);
        for (a = [0:15:90]) translate([0, 0, SH - SF + SF*sin(a) - 0.01]) linear_extrude(0.01) sokkel_2d(SF*(1 - cos(a)));
      }
      for (x = [-20, 20]) translate([x, 8, SH - 0.01]) cylinder(d = 4, h = 3.5, $fn = 24);                 // tapper til vugga
    }
    // gullstripa rundt toppen
    translate([0, 0, SH - gull_d]) linear_extrude(1) difference() { sokkel_2d(gull_inn); sokkel_2d(gull_inn + gull_b); }
    // vektlomme (åpen ned, lukkes med lokket) og gummiføtter
    translate([-vekt[0]/2, vekt_Y - vekt[1]/2, -0.01]) cube([vekt[0], vekt[1], vekt[2]]);
    translate([-vekt[0]/2 - 1, vekt_Y - vekt[1]/2 - 1, -0.01]) cube([vekt[0] + 2, vekt[1] + 2, 1.2]);   // fals for lokket
    for (x = [-SB/2 + 9, SB/2 - 9], y = [SY0 + 9, SY1 - 9]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h, $fn = 32);
    // ledningskanal: fra vugga rett ned, så bakover til USB-C (z 2–5) og fram til lysdioden
    translate([kanal_X, kanal_Y, 2]) cylinder(d = 4, h = SH, $fn = 20);
    hull() { translate([kanal_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true);
             translate([usb_X, SY1 - 2.5 - usb_kort[1] + 1, 3.5]) cube([4, 4, 3], center = true); }
    hull() { translate([kanal_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true);
             translate([led_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true); }
    translate([led_X - 2, SY0 + 2, 2]) cube([4, kanal_Y - SY0 - 2, 3]);
    // USB-C-brikken: lomme med kortet flatt, kontakten i bakkanten
    translate([usb_X - usb_kort[0]/2 - 0.2, SY1 - 2.5 - usb_kort[1], 2]) cube([usb_kort[0] + 0.4, usb_kort[1] + 0.2, usb_kort[2] + usb_k[2] + 0.4]);
    translate([usb_X, SY1 + 1, 2 + usb_kort[2] + usb_k[2]/2]) rotate([90, 0, 0])
      linear_extrude(4) offset(1.2) square([usb_k[0] + 0.4 - 2.4, usb_k[2] + 0.4 - 2.4], center = true);
    translate([usb_X, SY1 + 0.01, 2 + usb_kort[2] + usb_k[2]/2]) rotate([90, 0, 0])
      linear_extrude(1.2) offset(2.5) square([13.6 - 5, 7.4 - 5], center = true);                          // forsenkning for pluggen
    // lysdioden foran (valgfri)
    translate([led_X, SY0 - 1, 3.5]) rotate([-90, 0, 0]) cylinder(d = led_d, h = 4, $fn = 20);
    if (ir) ir_rom();
  }
}
// Delt sokkel: toppdelen er sokkelen over z = delt_z (åpen under, så USB-C-brikken, lysdioden, ledningene og vekten
// legges inn nedenfra), og en bunnplate på delt_z mm som skrus fast med fire selvgjengende M3 × 8 (eller M2,5 × 8).
// Gummiføttene sitter på bunnplata. Toppen og tappene til vugga er som før.
delt_z = 2.0;
skruer = [[-35.5, -10], [35.5, -10], [-35.5, 40], [35.5, 40]];   // fri for kanalene, vektlomma og USB-lomma
module sokkel_topp() {
  difference() {
    sokkel();
    translate([-200, -200, -1]) cube([400, 400, delt_z + 1]);
    for (p = skruer) translate([p[0], p[1], delt_z - 0.01]) cylinder(d = 2.6, h = 7, $fn = 20);   // forboring for skruene
  }
}
module sokkel_bunn() {
  difference() {
    hull() { translate([0, 0, 0.4]) linear_extrude(delt_z - 0.4) sokkel_2d(); linear_extrude(0.4) sokkel_2d(0.4); }
    for (p = skruer) translate([p[0], p[1], -0.01]) {
      cylinder(d = 3.4, h = delt_z + 1, $fn = 20);
      cylinder(d1 = 6.4, d2 = 3.4, h = 1.5, $fn = 32);                                              // senkehode under
    }
    for (x = [-SB/2 + 9, SB/2 - 9], y = [SY0 + 9, SY1 - 9]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h, $fn = 32);
  }
}
// ---------- IR: hull, lommer og kanaler (alt åpent ned mot bunnplata, så delene legges inn nedenfra) ----------
// Lokale koordinater for en lysdiode: origo i ytterflaten, +z ut langs aksen, +y omtrent opp (spissen på dråpen).
// yaw: 0 = fram (−Y), 180 = bak, 90 = høyre (+X); vippes ir_vinkel opp.
module ir_plass(p, yaw) { translate(p) rotate([0, 0, yaw]) rotate([90 - ir_vinkel, 0, 0]) children(); }
module draape2(d) { hull() { circle(d = d, $fn = 32); translate([0, d/2 * sqrt(2)]) circle(d = 0.05, $fn = 8); } }
module ir_hull_lokal() {
  trinn = ir_inne + ir_l - 1.0;                  // flensens forside (trinnet) fra ytterflaten
  translate([0, 0, -trinn]) linear_extrude(trinn + 3) draape2(ir_d);                          // gjennom
  translate([0, 0, -ir_fas]) cylinder(h = ir_fas + 3, d1 = ir_d, d2 = ir_d + 2*(ir_fas + 3), $fn = 32);   // fas
  translate([0, 0, -trinn - 10]) linear_extrude(10) draape2(ir_flens);                        // plass til flensen
}
module ir_led_lokal() {                          // lysdioden (bare for bildene og kollisjonssjekken)
  z0 = -ir_inne - ir_l;
  color([0.32, 0.36, 0.52, 0.95]) {
    translate([0, 0, z0]) cylinder(d = 5.8, h = 1.0, $fn = 32);
    translate([0, 0, z0 + 1]) cylinder(d = 4.95, h = ir_l - 1 - 2.47, $fn = 32);
    translate([0, 0, -ir_inne - 2.47]) sphere(d = 4.95, $fn = 32);
  }
  color([0.75, 0.75, 0.78]) for (x = [-1.27, 1.27]) translate([x, 0, z0 - 4]) cylinder(d = 0.5, h = 4, $fn = 8);
}
// plasseringen av lysdiodene (punkt i ytterflaten, yaw)
ir_front = [[[-ir_X, SY0, ir_z], -ir_spre], [[ir_X, SY0, ir_z], ir_spre]];
ir_ekstra = ir_tredje == "bak" ? [[[ir_bak_X, SY1, ir_z], 180]] : ir_tredje == "side" ? [[[SB/2, ir_side_Y, ir_z], 90]] : [];
ir_alle = concat(ir_front, ir_ekstra);
mott_z = delt_z + mott[2]/2 + 0.2;               // kuppelens senter (høyde)
module ir_kanal(a, b) { hull() { translate([a[0], a[1], delt_z + 1.5]) cube([4, 4, 3.02], center = true);
                                 translate([b[0], b[1], delt_z + 1.5]) cube([4, 4, 3.02], center = true); } }
module ir_rom() {
  z0 = delt_z - 0.01;
  // lysdiodene
  for (l = ir_alle) ir_plass(l[0], l[1]) ir_hull_lokal();
  // kammeret bak de fremre lysdiodene (transistor, motstander og ledninger)
  translate([-ir_kam[0]/2, SY0 + ir_kam[1], z0]) cube([ir_kam[0], ir_kam[2], 10 - delt_z]);
  // VS1838B: lomme fra kammeret og fram, og vindu med fas foran kuppelen
  if (ir_mottaker) {
    translate([-mott[0]/2 - 0.2, SY0 + 1.6, z0]) cube([mott[0] + 0.4, ir_kam[1] - 1.6 + 0.01, mott[2] + 0.4 + 0.01]);
    translate([0, SY0, mott_z]) rotate([90, 0, 0]) {
      translate([0, 0, -2]) linear_extrude(4) draape2(mott_vindu);
      translate([0, 0, -0.6]) cylinder(h = 3.6, d1 = mott_vindu, d2 = mott_vindu + 7.2, $fn = 32);
    }
  }
  // tredje lysdiode: et lite kammer bak hullet
  if (ir_tredje == "bak")
    translate([ir_bak_X - 4.5, SY1 - ir_kam[1] - 7, z0]) cube([9, 7.01, 10 - delt_z]);
  if (ir_tredje == "side")
    translate([SB/2 - ir_kam[1] - 7, ir_side_Y - 4.5, z0]) cube([7.01, 9, 10 - delt_z]);
  // ESP32-C3 SuperMini: flatt på bunnplata, USB-enden bakover; ledningene loddes ovenfra
  translate([c3_X - c3[0]/2 - 0.2, c3_Y - c3[1]/2 - 0.2, z0]) cube([c3[0] + 0.4, c3[1] + 1.6, c3[2] + 2.5]);   // + 1,2 for USB-C-en
  // lysleder over den blå lysdioden (en bit klar filament, 1,75 mm)
  translate([c3_X + c3_lys[0], c3_Y + c3_lys[1], 2]) cylinder(d = lysleder_d, h = SH, $fn = 16);
  // ledningskanaler (z 2–5): kammeret foran → langs venstre side → C3; C3 → USB-C-brikken (5 V og GND)
  ir_kanal([-ir_kam[0]/2 + 1, SY0 + ir_kam[1] + 2], [-22, SY0 + ir_kam[1] + 2]);
  ir_kanal([-22, SY0 + ir_kam[1] + 2], [-22, c3_Y - c3[1]/2 + 2]);
  ir_kanal([c3_X + c3[0]/2 - 1, SY1 - 13], [usb_X - usb_kort[0]/2 + 1, SY1 - 13]);
  if (ir_tredje == "bak") ir_kanal([usb_X + usb_kort[0]/2 - 1, SY1 - 13], [ir_bak_X, SY1 - 13]);
  if (ir_tredje == "side") ir_kanal([SB/2 - ir_kam[1] - 5, ir_side_Y], [kanal_X, kanal_Y]);
}
// de kjøpte delene i IR-dokka (for bildene og kollisjonssjekken)
module ir_deler() {
  for (l = ir_alle) ir_plass(l[0], l[1]) ir_led_lokal();
  if (ir_mottaker) translate([0, SY0 + 1.6 + 0.05, delt_z + 0.2]) {            // VS1838B liggende, kuppelen fram
    color([0.08, 0.08, 0.09]) translate([-mott[0]/2 + 0.1, 0.9, 0]) cube([mott[0] - 0.2, mott[1] - 0.9, mott[2]]);
    color([0.08, 0.08, 0.09]) translate([0, 0.9, mott[2]/2]) rotate([90, 0, 0]) cylinder(d = 3.6, h = 0.9, $fn = 24);
  }
  // ESP32-C3 SuperMini
  translate([c3_X, c3_Y, delt_z]) {
    color([0.12, 0.18, 0.40]) translate([-c3[0]/2, -c3[1]/2, 0]) cube([c3[0], c3[1], 1.0]);
    color([0.15, 0.15, 0.16]) translate([-2.5, -2.5, 1]) cube([5, 5, 0.9]);                            // ESP32-C3
    color([0.75, 0.75, 0.78]) translate([-4.5, c3[1]/2 - 7.3 + 1.0, 1]) cube([9, 7.3, 3.2]);           // USB-C
    color([0.85, 0.85, 0.82]) translate([-5, -c3[1]/2 + 0.5, 1]) cube([10, 2.5, 1]);                   // antenne
    color([0.3, 0.5, 1.0]) translate([c3_lys[0] - 0.5, c3_lys[1] - 0.4, 1]) cube([1, 0.8, 0.5]);       // blå lysdiode
  }
  // USB-C-brikken (til strøm for både dokka og C3)
  translate([usb_X, SY1 - 2.5 - usb_kort[1]/2, delt_z]) {
    color([0.15, 0.35, 0.2]) translate([-usb_kort[0]/2, -usb_kort[1]/2, 0]) cube(usb_kort);
    color([0.75, 0.75, 0.78]) translate([-usb_k[0]/2, usb_kort[1]/2 - usb_k[1] + 0.6, usb_kort[2]]) cube(usb_k);
  }
  // driverkort (AO3400 + motstander på et lite hullkort), stående mot bakveggen i kammeret
  color([0.15, 0.35, 0.2]) translate([-8, SY0 + ir_kam[1] + ir_kam[2] - 1.8, delt_z + 0.3]) cube([16, 1.6, 6]);
}

module gull() { translate([0, 0, SH - gull_d]) linear_extrude(gull_d) difference() { sokkel_2d(gull_inn + 0.08); sokkel_2d(gull_inn + gull_b - 0.08); } }
module lokk() { translate([-vekt[0]/2 - 0.9, vekt_Y - vekt[1]/2 - 0.9, 0]) cube([vekt[0] + 1.8, vekt[1] + 1.8, 1.15]); }
module pogo_han() { fk_plass() pogo_han_lokal(); }
// propp til lysdiodehullet foran, for deg som ikke vil ha lys: trykkes inn (en dråpe lim) og er i flukt med fronten.
// Printes stående med den flate enden ned, i samme farge som sokkelen.
module led_propp() { cylinder(d = led_d - 0.15, h = 3.2, $fn = 32); }

c_topp = farge == "bone" ? [0.81, 0.78, 0.71] : [0.17, 0.17, 0.18];
c_sokkel = farge == "bone" ? [0.17, 0.17, 0.18] : [0.82, 0.80, 0.75];
c_gull = [0.85, 0.62, 0.25];
module samlet() { color(c_topp) vugge(); color(c_sokkel) sokkel(); color(c_gull) gull(); pogo_han(); if (ir) ir_deler(); }
// IR-dokka sett inni: sokkelen kuttet i z = 4,6 (lommene og kanalene synes) med bunnplata og delene på plass
module ir_inni() {
  color(c_sokkel) intersection() { sokkel_topp(); translate([-100, -100, 0]) cube([200, 200, 4.6]); }
  color(c_sokkel * 0.85) translate([0, 0, -0.02]) sokkel_bunn();
  ir_deler();
}

if (part == "vugge") vugge();
else if (part == "sokkel") sokkel();
else if (part == "gull") gull();
else if (part == "lokk") lokk();
else if (part == "pogo_han") pogo_han();
else if (part == "led_propp") led_propp();
else if (part == "sokkel_topp") sokkel_topp();
else if (part == "sokkel_bunn") sokkel_bunn();
else if (part == "samlet") samlet();
else if (part == "ir_deler") ir_deler();
else if (part == "ir_inni") ir_inni();
else if (part == "med_fjernkontroll") {
  samlet();
  fk_plass() {   // fjernkontrollen (STL-ene fra lag_stl.sh, montert stilling)
    D = variant == "kort" ? "../asm/" : "../asm_full/";
    color(farge == "bone" ? [0.81, 0.78, 0.71] : [0.93, 0.92, 0.89]) import(str(D, "topp.stl"));
    color(farge == "bone" ? [0.17, 0.17, 0.18] : [0.2, 0.2, 0.2]) import(str(D, "bunn.stl"));
    color([0.18, 0.18, 0.18]) import(str(D, "hetter.stl"));
    color([0.93, 0.92, 0.89]) import(str(D, "symboler.stl"));
    color(c_gull) import(str(D, "logo.stl"));
  }
}
else if (part == "profil") projection(cut = true) rotate([0, 90, 0]) samlet();
