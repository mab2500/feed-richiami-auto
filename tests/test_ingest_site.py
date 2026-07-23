from inkscout.core.models import SourceRef
from inkscout.ingest import base
from inkscout.ingest.site import PersonalSiteAdapter, extract_image_urls

HTML = """
<html><head>
<meta property="og:image" content="/img/hero.jpg">
<script type="application/ld+json">{"@type":"ImageObject","image":"https://cdn.ex/j.png"}</script>
</head><body>
<img src="a.jpg" srcset="a-2x.jpg 2x, a-3x.jpg 3x">
<img src="/img/hero.jpg">
</body></html>
"""


def test_extract_dedup_and_absolute():
    urls = extract_image_urls(HTML, "https://site.ex/gallery/")
    assert "https://site.ex/img/hero.jpg" in urls
    assert "https://site.ex/gallery/a.jpg" in urls
    assert "https://cdn.ex/j.png" in urls
    assert urls.count("https://site.ex/img/hero.jpg") == 1  # deduplicato


def test_fetch_emits_rawitems(tmp_path, monkeypatch):
    monkeypatch.setattr(
        base,
        "_http_get",
        lambda url: HTML.encode() if url.endswith("gallery/") else b"IMGBYTES",
    )
    items = list(
        PersonalSiteAdapter(cache_dir=tmp_path).fetch(
            SourceRef(kind="site", ref="https://site.ex/gallery/")
        )
    )
    assert len(items) >= 3
    assert all(i.image_bytes == b"IMGBYTES" for i in items)
    assert all(i.license_note == "personal-site" for i in items)
