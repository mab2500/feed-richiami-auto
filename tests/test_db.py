from inkscout.store.db import Store


def _store(tmp_path):
    return Store(tmp_path / "t.db")


def test_wal_enabled(tmp_path):
    s = _store(tmp_path)
    mode = s.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_add_and_get_image_with_provenance(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("site", "https://artist.example")
    art = s.add_artist("Jane", handle="@jane", source_id=src)
    img = s.add_image(
        path="images/a.jpg",
        phash=123,
        width=800,
        height=600,
        artist_id=art,
        source_id=src,
        source_url="https://artist.example/a",
        license_note="personal-reference",
        fetched_at="2026-07-23T10:00:00",
    )
    row = s.get_image(img)
    assert row["source_url"] == "https://artist.example/a"
    assert row["license_note"] == "personal-reference"
    assert row["favorite"] == 0 and row["hidden"] == 0


def test_favorite_hidden_and_listing(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("upload", "local")
    a = s.add_image("images/a.jpg", 1, 10, 10, None, src, "u://a", "n", "t")
    b = s.add_image("images/b.jpg", 2, 10, 10, None, src, "u://b", "n", "t")
    s.set_favorite(a, True)
    s.set_hidden(b, True)
    visible = s.list_images()
    ids = {r["id"] for r in visible}
    assert a in ids and b not in ids  # hidden escluso di default
    assert any(r["favorite"] == 1 for r in visible)


def test_style_upsert_is_idempotent(tmp_path):
    s = _store(tmp_path)
    id1 = s.upsert_style("blackwork", description="tratto pieno")
    id2 = s.upsert_style("blackwork", description="aggiornata")
    assert id1 == id2
    assert s.style_id_by_name("blackwork") == id1


def test_all_phashes_for_dedup(tmp_path):
    s = _store(tmp_path)
    src = s.add_source("upload", "local")
    s.add_image("images/a.jpg", 111, 10, 10, None, src, "u://a", "n", "t")
    s.add_image("images/b.jpg", 222, 10, 10, None, src, "u://b", "n", "t")
    pairs = dict(s.all_phashes())
    assert set(pairs.values()) == {111, 222}
