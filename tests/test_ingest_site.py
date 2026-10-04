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


HTML_JSONLD = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"WebPage","image":["https://cdn.ex/a.jpg","https://cdn.ex/b.jpg"]},
  {"@type":"Article","image":{"@type":"ImageObject","url":"https://cdn.ex/c.jpg"}}
]}
</script>
<script type="text/javascript">var cfg = {"image":"/falso.jpg"};</script>
</head><body>
<p>nel body c'e' un "image":"/falso2.jpg" come testo qualsiasi</p>
</body></html>
"""


def test_jsonld_array_object_and_no_false_positive():
    urls = extract_image_urls(HTML_JSONLD, "https://site.ex/g/")
    # (a) image come lista di stringhe dentro ld+json -> entrambe
    assert "https://cdn.ex/a.jpg" in urls
    assert "https://cdn.ex/b.jpg" in urls
    # (b) image come ImageObject con chiave url -> c.jpg
    assert "https://cdn.ex/c.jpg" in urls
    # (c) "image" fuori dai blocchi ld+json (script JS o body) -> NON deve comparire
    assert "https://site.ex/falso.jpg" not in urls
    assert "https://site.ex/falso2.jpg" not in urls


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
