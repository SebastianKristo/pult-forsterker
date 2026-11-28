"""Podme (pi/skjold_podme.py) i podkastene (pi/skjold_pod.py): formatet, favoritter, søk og avspilling – uten nett."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_pod as P  # noqa: E402
import skjold_podme as M  # noqa: E402


class FalskPodme:
    """Står i for Podme-klienten (ingen innlogging eller nett)."""
    def __init__(self):
        self.fulgt = []

    def my_podcasts(self):
        return [M.Podme.show_of({"id": 7, "title": "Premium-podden", "authorFullName": "Podme", "largeImageUrl": "https://p/7.jpg", "isPremium": True})]

    def search(self, q):
        return [M.Podme.show_of({"id": 8, "title": "Lydlab", "imageUrl": "https://p/8.jpg"})]

    def show(self, pid):
        return {**M.Podme.show_of({"id": pid, "title": "Premium-podden"}),
                "episodes": [M.Podme.episode_of({"id": 70, "podcastId": pid, "title": "Ep 1", "length": "00:30:00", "publishDate": "2026-11-20T06:00:00Z"})]}

    def feed(self, n=30):
        return [M.Podme.episode_of({"id": 71, "podcastId": 7, "podcastTitle": "Premium-podden", "title": "Ny", "length": 600, "publishDate": "2026-11-27T06:00:00Z"})]

    def follow(self, pid, on):
        self.fulgt.append((pid, on))

    def audio_url(self, eid):
        return f"https://cdn.podme/{eid}.mp4"

    def me(self):
        return {"user": "a@b.no"}


class PodmeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.pod = P.Pod(self.dir, fetch=lambda u: b"{}", settings=lambda: {"podmeEmail": "a@b.no", "podmePass": "x"})
        self.fake = FalskPodme()
        self.pod._podme = ("a@b.no", "x", self.fake)

    def test_formatet(self):
        s = M.Podme.show_of({"podcastId": 5, "podcastTitle": "T", "mediumImageUrl": "https://i", "categories": [{"name": "Nyheter"}]})
        self.assertEqual((s["id"], s["src"], s["image"], s["genre"]), ("podme:5", "podme", "https://i", "Nyheter"))
        e = M.Podme.episode_of({"id": 9, "podcastId": 5, "title": "E", "length": "01:02:03", "currentSpotSec": 60, "publishDate": "2026-11-28T08:00:00Z"})
        self.assertEqual((e["id"], e["url"], e["duration"], e["pos"], e["date"], e["pid"]), ("podme-9", "podme:9", 3723.0, 60.0, "28.11.2026", "podme:5"))
        self.assertTrue(M.Podme.episode_of({"id": 1, "hasCompleted": True, "length": 100})["heard"])

    def test_favoritter_med_podme(self):
        ids = [x["id"] for x in self.pod.all_favs()]
        self.assertIn("podme:7", ids)
        self.pod.fav(add={"id": "podme:8", "title": "Lydlab"})
        self.assertEqual(self.fake.fulgt, [(8, True)])
        self.assertTrue(self.pod.favs.has("podme:8"))
        self.pod.fav(remove="podme:8")
        self.assertEqual(self.fake.fulgt[-1], (8, False))

    def test_sok_tar_med_podme(self):
        self.pod.fetch = lambda u: b'{"results": [{"collectionId": 1, "collectionName": "Lydlab", "artistName": "A", "feedUrl": "https://x/f.xml"}]}'
        res = self.pod.search("lydlab")
        self.assertEqual(res[0]["src"], "podme")
        self.assertEqual(sum(1 for x in res if x["title"] == "Lydlab"), 1)

    def test_show_og_nye_episoder(self):
        s = self.pod.show("podme:7")
        self.assertEqual((s["id"], s["src"], s["episodes"][0]["url"]), ("podme:7", "podme", "podme:70"))
        self.assertIn("podme-71", [e["id"] for e in self.pod.new_episodes()])

    def test_lydadressen_byttes(self):
        self.assertEqual(self.pod.resolve("podme:70"), "https://cdn.podme/70.mp4")
        self.assertEqual(self.pod.resolve("https://x/a.mp3"), "https://x/a.mp3")

    def test_uten_innlogging(self):
        pod = P.Pod(self.dir, fetch=lambda u: b"{}", settings=lambda: {})
        self.assertIsNone(pod.podme())
        self.assertEqual(pod.podme_status(), {"configured": False})
        with self.assertRaises(P.PodError):
            pod.resolve("podme:1")


if __name__ == "__main__":
    unittest.main()
