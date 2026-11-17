"""Podkaster (pi/skjold_pod.py): toppliste, søk, RSS, favoritter og nye episoder – mot falske svar."""
import json
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_pod as P  # noqa: E402

RSS = b"""<?xml version="1.0"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0"><channel>
<title>Lydlab</title><itunes:author>Skjold</itunes:author><itunes:image href="https://x/lydlab.jpg"/>
<description>&lt;p&gt;Om lyd&lt;/p&gt;</description>
<item><title>Ep 1</title><pubDate>Mon, 02 Nov 2026 06:00:00 GMT</pubDate><itunes:duration>12:30</itunes:duration>
<enclosure url="https://x/ep1.mp3" type="audio/mpeg"/></item>
<item><title>Ep 2</title><pubDate>Mon, 09 Nov 2026 06:00:00 GMT</pubDate><itunes:duration>3725</itunes:duration>
<enclosure url="https://x/ep2.mp3" type="audio/mpeg"/><itunes:image href="https://x/ep2.jpg"/></item>
<item><title>Video</title><enclosure url="https://x/v.mp4" type="video/mp4"/></item>
</channel></rss>"""

TOP_OLD = {"feed": {"entry": [{"id": {"attributes": {"im:id": "111"}}, "im:name": {"label": "Topp 1"}, "im:artist": {"label": "Kanal"},
                               "im:image": [{"label": "https://a/55x55bb.png"}, {"label": "https://a/170x170bb.png"}],
                               "category": {"attributes": {"label": "Nyheter"}}}]}}
TOP_NEW = {"feed": {"results": [{"id": "222", "name": "Ny topp", "artistName": "B", "artworkUrl100": "https://b/100x100bb.jpg", "genres": [{"name": "Komedie"}]}]}}
SEARCH = {"results": [{"collectionId": 333, "collectionName": "Lydlab", "artistName": "Skjold", "artworkUrl600": "https://x/600x600bb.jpg",
                       "feedUrl": "https://x/feed.xml", "primaryGenreName": "Teknologi"}]}


class Falsk:
    def __init__(self, svar):
        self.svar, self.kall = svar, []

    def __call__(self, url):
        self.kall.append(url)
        for k, v in self.svar.items():
            if k in url:
                if isinstance(v, Exception):
                    raise v
                return v if isinstance(v, bytes) else json.dumps(v).encode()
        raise P.PodError("404")


class TestParse(unittest.TestCase):
    def test_rss(self):
        s = P.parse_rss(RSS)
        self.assertEqual((s["title"], s["author"], s["image"], s["description"]), ("Lydlab", "Skjold", "https://x/lydlab.jpg", "Om lyd"))
        self.assertEqual([e["title"] for e in s["episodes"]], ["Ep 2", "Ep 1"])   # nyeste først, uten video
        self.assertEqual(s["episodes"][0]["duration"], 3725)
        self.assertEqual(s["episodes"][1]["duration"], 750)
        self.assertEqual(s["episodes"][0]["image"], "https://x/ep2.jpg")
        self.assertEqual(s["episodes"][1]["image"], "https://x/lydlab.jpg")
        self.assertEqual(s["episodes"][0]["date"], "2026-11-09")
        self.assertEqual(s["episodes"][0]["id"], P.ep_id("https://x/ep2.mp3"))

    def test_ikke_rss(self):
        with self.assertRaises(P.PodError):
            P.parse_rss(b"<html><body>hei</body></html>")

    def test_topplister(self):
        a = P.parse_top(TOP_OLD)[0]
        self.assertEqual((a["id"], a["title"], a["image"], a["genre"]), ("apple:111", "Topp 1", "https://a/600x600bb.png", "Nyheter"))
        b = P.parse_top(TOP_NEW)[0]
        self.assertEqual((b["id"], b["image"]), ("apple:222", "https://b/600x600bb.jpg"))

    def test_varighet(self):
        self.assertEqual(P._secs("1:02:03"), 3723)
        self.assertEqual(P._secs(""), 0)
        self.assertEqual(P._secs("tull"), 0)


class TestPod(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.f = Falsk({"/search?": SEARCH, "toppodcasts/limit=100/genre=1303": TOP_OLD, "toppodcasts/limit=100/json": P.PodError("nede"),
                        "applemarketingtools": TOP_NEW, "lookup?": SEARCH, "x/feed.xml": RSS, "egen.no/rss": RSS})
        self.p = P.Pod(self.dir, fetch=self.f)

    def test_toppliste_faller_tilbake_og_caches(self):
        self.assertEqual(self.p.top()[0]["title"], "Ny topp")
        n = len(self.f.kall)
        self.p.top()
        self.assertEqual(len(self.f.kall), n)
        self.assertEqual(self.p.top(1303)[0]["title"], "Topp 1")

    def test_sok_og_show(self):
        r = self.p.search("lyd")
        self.assertEqual(r[0]["id"], "apple:333")
        self.assertNotIn("feed", r[0])
        s = self.p.show("apple:333")
        self.assertEqual((s["title"], s["src"], s["fav"], len(s["episodes"])), ("Lydlab", "apple", False, 2))

    def test_show_slaar_opp_strommen(self):
        s = self.p.show("apple:333")   # ikke søkt først: lookup gir feedUrl
        self.assertEqual(s["title"], "Lydlab")
        self.assertTrue(any("lookup?" in u for u in self.f.kall))

    def test_rss_adresse_i_sok(self):
        r = self.p.search("https://egen.no/rss")
        self.assertEqual(r, [{"id": "rss:https://egen.no/rss", "title": "Lydlab", "author": "Skjold", "image": "https://x/lydlab.jpg", "src": "rss"}])

    def test_favoritter_lagres_og_nye_episoder(self):
        self.p.favs.add({"id": "apple:333", "title": "Lydlab", "image": "https://x/i.jpg"})
        self.p.favs.add({"id": "rss:https://egen.no/rss", "title": "Egen"})
        with self.assertRaises(P.PodError):
            self.p.favs.add({"id": "javascript:alert(1)"})
        p2 = P.Pod(self.dir, fetch=self.f)
        self.assertEqual([x["id"] for x in p2.favs.items], ["apple:333", "rss:https://egen.no/rss"])
        self.assertTrue(p2.show("apple:333")["fav"])
        nye = p2.new_episodes()
        self.assertEqual(len(nye), 4)
        self.assertEqual(nye[0]["title"], "Ep 2")
        p2.favs.remove("apple:333")
        self.assertEqual([x["id"] for x in P.Pod(self.dir, fetch=self.f).favs.items], ["rss:https://egen.no/rss"])

    def test_fremdrift_vises_paa_episoden(self):
        eid = P.ep_id("https://x/ep1.mp3")
        self.p.progress.update(eid, 300, 750, {"title": "Ep 1"})
        e = [x for x in self.p.show("apple:333")["episodes"] if x["id"] == eid][0]
        self.assertEqual(e["pos"], 300)
        self.assertEqual(self.p.continue_list()[0]["id"], eid)

    def test_nrk_i_sok_og_show(self):
        class N:
            progress = type("Pr", (), {"get": staticmethod(lambda eid: {})})()
            def search(self, q): return {"series": [{"id": "abels-taarn", "title": "Abels tårn", "image": "https://n/i.jpg", "kind": "series"}]}
            def series(self, sid, kind=""): return {"title": "Abels tårn", "image": "https://n/i.jpg", "subtitle": "", "kind": "series",
                                                    "episodes": [{"id": "MSUS1", "title": "Del 1", "duration": 60, "podcast": False}]}
        p = P.Pod(self.dir, fetch=self.f, nrk=N())
        r = p.search("abels")
        self.assertEqual(r[0]["id"], "nrk:abels-taarn")
        s = p.show("nrk:abels-taarn")
        self.assertEqual((s["src"], s["episodes"][0]["nrk"], s["episodes"][0]["id"]), ("nrk", True, "MSUS1"))


if __name__ == "__main__":
    unittest.main()
