import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_homelayout as H   # noqa: E402


def test_clean_rejects_garbage_and_duplicates():
    assert H.clean("x") == [] and H.clean(None) == []
    v = [{"id": "favs", "visible": False}, {"id": "favs"}, "recent", {"id": "Bad Id!"}, 5, {"id": "nytt_fra_framtiden"}]
    assert H.clean(v) == [{"id": "favs", "visible": False}, {"id": "recent", "visible": True}, {"id": "nytt_fra_framtiden", "visible": True}]


def test_resolved_keeps_order_and_appends_missing():
    r = H.resolved([{"id": "sources", "visible": True}, {"id": "favs", "visible": False}], ["recent", "favs", "sources"])
    assert [x["id"] for x in r] == ["sources", "favs", "recent"]
    assert r[1]["visible"] is False and r[2]["visible"] is True


def test_default_is_all_known_visible():
    r = H.resolved([])
    assert [x["id"] for x in r] == [s for s, _ in H.SECTIONS] and all(x["visible"] for x in r)


def test_max_items():
    assert len(H.clean([{"id": f"s{i}"} for i in range(100)])) == H.MAX_ITEMS
