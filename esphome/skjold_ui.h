// Skjold Fjernkontroll – hjelpefunksjoner for skjermen (tas med av esphome: includes i skjold-fjernkontroll*.yaml).
// Bare rene funksjoner og hurtigbuffer i RTC-minnet: ingen id(...) her, siden fila tas med før komponentene.
#pragma once
#include <string>
#include <vector>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include "esp_attr.h"
#include "esp_sleep.h"

namespace skjold {

// Hurtigbuffer som overlever dyp søvn (RTC-minne, ingen flash-slitasje): skjermen viser siste kjente tilstand med en
// gang den våkner, og oppdateres når Home Assistant og Skjold svarer.
RTC_DATA_ATTR static char rtc_apper[768];      // Apple TV source_list, «|»-delt
RTC_DATA_ATTR static char rtc_atv_tittel[96];
RTC_DATA_ATTR static char rtc_atv_app[48];
RTC_DATA_ATTR static char rtc_atv_tilstand[16];
RTC_DATA_ATTR static char rtc_tv_kilde[32];
RTC_DATA_ATTR static char rtc_skjold_tittel[96];
RTC_DATA_ATTR static char rtc_skjold_artist[96];
RTC_DATA_ATTR static uint32_t rtc_magi;        // 0x534B4A44 når bufferet er gyldig

inline void rtc_sett(char *mal, size_t n, const std::string &s) {
  strncpy(mal, s.c_str(), n - 1);
  mal[n - 1] = 0;
}
inline void rtc_klar() {
  if (rtc_magi != 0x534B4A44u) {
    rtc_apper[0] = rtc_atv_tittel[0] = rtc_atv_app[0] = rtc_atv_tilstand[0] = 0;
    rtc_tv_kilde[0] = rtc_skjold_tittel[0] = rtc_skjold_artist[0] = 0;
    rtc_magi = 0x534B4A44u;
  }
}

// Home Assistant sender lister som Python-tekst: "['Netflix', 'YouTube', \"Disney+\"]". Godtar også «a|b|c».
inline std::vector<std::string> les_liste(const std::string &s) {
  std::vector<std::string> ut;
  if (s.empty()) return ut;
  if (s[0] != '[') {
    size_t a = 0;
    while (a <= s.size()) {
      size_t b = s.find('|', a);
      if (b == std::string::npos) b = s.size();
      if (b > a) ut.push_back(s.substr(a, b - a));
      a = b + 1;
    }
    return ut;
  }
  size_t i = 1;
  while (i < s.size()) {
    char q = s[i];
    if (q == '\'' || q == '"') {
      std::string v;
      i++;
      while (i < s.size() && s[i] != q) {
        if (s[i] == '\\' && i + 1 < s.size()) i++;
        v += s[i++];
      }
      ut.push_back(v);
    }
    i++;
  }
  return ut;
}

inline std::string slaa_sammen(const std::vector<std::string> &v) {
  std::string s;
  for (size_t i = 0; i < v.size(); i++) s += (i ? "|" : "") + v[i];
  return s;
}

// Første tegn (UTF-8) i et ord
inline std::string forste_tegn(const std::string &s, size_t i) {
  unsigned char c = s[i];
  size_t n = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : 4;
  return s.substr(i, n);
}

// Initialer til appflisa: «Apple TV+» → «AT», «Netflix» → «Ne», «NRK TV» → «NT»
inline std::string initialer(const std::string &navn) {
  std::vector<size_t> start;
  for (size_t i = 0; i < navn.size(); i++)
    if (navn[i] != ' ' && (i == 0 || navn[i - 1] == ' ')) start.push_back(i);
  if (start.empty()) return "?";
  if (start.size() >= 2) return forste_tegn(navn, start[0]) + forste_tegn(navn, start[1]);
  std::string a = forste_tegn(navn, start[0]);
  if (a.size() + start[0] < navn.size()) {
    std::string b = forste_tegn(navn, start[0] + a.size());
    if (b.size() == 1 && b[0] >= 'A' && b[0] <= 'Z') b[0] = b[0] - 'A' + 'a';
    return a + b;
  }
  return a;
}

// Dempet farge fra navnet (samme navn gir alltid samme farge), mørk nok til lys tekst
inline uint32_t flisfarge(const std::string &navn) {
  static const uint32_t P[10] = {0x7A2E2E, 0x2E4F7A, 0x2E6B4F, 0x6B4F2E, 0x5A2E6B, 0x2E6468,
                                 0x6B2E52, 0x46572E, 0x3B3B6E, 0x6E4A2E};
  uint32_t h = 2166136261u;
  for (unsigned char c : navn) h = (h ^ c) * 16777619u;
  return P[h % 10];
}

// mm:ss eller t:mm:ss
inline std::string tid(int s) {
  if (s < 0) s = 0;
  char b[16];
  if (s >= 3600) snprintf(b, sizeof b, "%d:%02d:%02d", s / 3600, (s / 60) % 60, s % 60);
  else snprintf(b, sizeof b, "%d:%02d", s / 60, s % 60);
  return b;
}

// ---------- tastene: kort, langt og dobbelt trykk uten ventetid der det trengs ----------
// · Straks-taster (D-pad, OK, volum, spill/pause …) sendes i det de trykkes. Piler, volum og ± gjentas når de holdes
//   (første gang etter 400 ms, så hvert 120 ms).
// · Taster med langt trykk (av, Skjold-tasten, meny, tilbake, avslutt, lys, stikk) sendes når de slippes, eller som
//   «lang» etter 600 ms. Av, Skjold, meny, lys og stikk venter i tillegg 250 ms etter slipp på et dobbelttrykk.
// · send(navn, type) kalles med type "kort", "lang", "dobbel" eller "gjenta" (gjentatt mens tasten holdes).
struct Tastatur {
  static constexpr uint32_t LANG_MS = 600, DOBBEL_MS = 250, GJENTA_FORST_MS = 400, GJENTA_MS = 120;
  struct T { bool ned = false, lang_sendt = false; uint32_t t_ned = 0, t_opp = 0, neste = 0; int klikk = 0; };
  std::vector<std::pair<std::string, T>> taster;
  void (*send)(const std::string &, const char *) = nullptr;
  std::string ignorer;            // tasten som vekket den (allerede sendt) – neste trykk/slipp innen 1,5 s ignoreres
  uint32_t ignorer_til = 0;

  static bool i(const std::string &n, std::initializer_list<const char *> l) {
    for (auto *x : l) if (n == x) return true;
    return false;
  }
  static bool gjentas(const std::string &n) { return i(n, {"opp", "ned", "venstre", "hoyre", "vol_opp", "vol_ned", "pluss", "minus"}); }
  static bool treg(const std::string &n) { return i(n, {"av", "hjem", "meny", "tilbake", "avslutt", "lys", "stikk"}); }
  static bool dobbel(const std::string &n) { return i(n, {"av", "hjem", "meny", "lys", "stikk"}); }
  T &finn(const std::string &n) {
    for (auto &p : taster) if (p.first == n) return p.second;
    taster.emplace_back(n, T{});
    return taster.back().second;
  }
  void ut(const std::string &n, const char *type) { if (send) send(n, type); }
  void ned(const std::string &n, uint32_t na) {
    if (n.empty()) return;
    if (n == ignorer && na < ignorer_til) return;
    T &t = finn(n);
    if (t.ned) return;
    t.ned = true; t.t_ned = na; t.lang_sendt = false;
    if (!treg(n)) {
      ut(n, "kort");
      if (gjentas(n)) t.neste = na + GJENTA_FORST_MS;
      return;
    }
    if (t.klikk == 1 && na - t.t_opp < DOBBEL_MS) t.klikk = 2;
  }
  void opp(const std::string &n, uint32_t na) {
    if (n.empty()) return;
    if (n == ignorer && na < ignorer_til) { finn(n).ned = false; return; }
    T &t = finn(n);
    if (!t.ned) return;
    t.ned = false;
    if (!treg(n) || t.lang_sendt) { t.klikk = 0; return; }
    if (t.klikk == 2) { t.klikk = 0; ut(n, "dobbel"); return; }
    if (dobbel(n)) { t.klikk = 1; t.t_opp = na; return; }
    ut(n, "kort");
  }
  void tikk(uint32_t na) {
    for (auto &p : taster) {
      T &t = p.second;
      if (t.ned && gjentas(p.first) && (int32_t) (na - t.neste) >= 0) { ut(p.first, "gjenta"); t.neste = na + GJENTA_MS; }
      if (t.ned && treg(p.first) && !t.lang_sendt && (int32_t) (na - t.t_ned) >= (int32_t) LANG_MS) { t.lang_sendt = true; t.klikk = 0; ut(p.first, "lang"); }
      if (!t.ned && t.klikk == 1 && (int32_t) (na - t.t_opp) >= (int32_t) DOBBEL_MS) { t.klikk = 0; ut(p.first, "kort"); }
    }
  }
  bool noen_nede() const {
    for (auto &p : taster) if (p.second.ned || p.second.klikk) return true;
    return false;
  }
};
inline Tastatur tastatur;

}  // namespace skjold
