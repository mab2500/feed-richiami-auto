"""Adapter WhatsApp: parsing dei dialetti di export, artista dal contesto, privacy.

Le fixture riproducono i formati veri (iOS/Android, IT/EN) inclusi i marcatori di
direzione invisibili che WhatsApp infila e che rompono i parser ingenui.
"""

from pathlib import Path

from PIL import Image

from inkscout.core.models import SourceRef
from inkscout.ingest.whatsapp import (
    MAX_CONTESTO,
    contesto,
    estrai_allegato,
    estrai_handle,
    handle_vicino,
    parse_export,
    trova_export,
    WhatsAppAdapter,
)

# due foto, due tatuatori diversi: è il caso che ha smascherato l'attribuzione sfasata
DUE_ARTISTI = (
    "[06/09/24, 21:14:02] Matteo: guarda che roba\n"
    "[06/09/24, 21:14:20] Matteo: ‎<allegato: FOTO-1.jpg>\n"
    "[06/09/24, 21:15:01] Matteo: è di @dario.ink\n"
    "[07/09/24, 09:00:00] Giulia: questo mi piace di più\n"
    "[07/09/24, 09:00:10] Giulia: ‎<allegato: FOTO-2.jpg>\n"
    "[07/09/24, 09:01:00] Giulia: https://www.instagram.com/ann_tattoo/ lo fa lei\n"
)

# iOS: parentesi quadre, `<allegato: …>`, U+200E prima dell'allegato
IOS = (
    "[06/09/24, 21:14:02] Matteo: Guarda che roba\n"
    "[06/09/24, 21:14:20] Matteo: ‎<allegato: 00000042-PHOTO-2024-09-06-21-14-20.jpg>\n"
    "[06/09/24, 21:15:01] Matteo: è di @dario.ink, studio a Pisa\n"
    "[06/09/24, 21:16:00] Giulia: bello ma lo vorrei\n"
    "più piccolo sul polso\n"
)

# Android: niente quadre, ` - ` come separatore, `(file allegato)`
ANDROID = (
    "12/01/24, 18:02 - Giulia: questo serpente fine-line\n"
    "12/01/24, 18:02 - Giulia: IMG-20240112-WA0007.jpg (file allegato)\n"
    "12/01/24, 18:03 - Giulia: https://www.instagram.com/ann_tattoo/ lo fa lei\n"
)


def _scrivi_export(tmp_path, testo, nome="_chat.txt", immagini=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / nome).write_text(testo, encoding="utf-8")
    for img in immagini:
        Image.new("RGB", (16, 16), (30, 30, 30)).save(tmp_path / img)
    return tmp_path


def test_parse_ios_con_caratteri_invisibili():
    msgs = parse_export(IOS)
    assert len(msgs) == 4
    assert msgs[0].mittente == "Matteo" and msgs[0].data == "06/09/24"
    assert msgs[1].allegato == "00000042-PHOTO-2024-09-06-21-14-20.jpg"
    assert msgs[3].mittente == "Giulia"
    # la riga senza timestamp è la continuazione del messaggio precedente
    assert "più piccolo sul polso" in msgs[3].testo


def test_parse_android():
    msgs = parse_export(ANDROID)
    assert len(msgs) == 3
    assert msgs[1].allegato == "IMG-20240112-WA0007.jpg"
    assert msgs[0].mittente == "Giulia"


def test_estrai_allegato_dialetti_e_non_immagini():
    assert estrai_allegato("<attached: foto.png>") == "foto.png"
    assert estrai_allegato("VID-20240101-WA0001.mp4 (file allegato)") is None  # non è immagine
    assert estrai_allegato("immagine omessa") is None                          # export senza media
    assert estrai_allegato("nessun allegato qui") is None


def test_estrai_handle_e_falsi_positivi():
    assert estrai_handle("è di @dario.ink, studio a Pisa") == "@dario.ink"
    assert estrai_handle("https://www.instagram.com/ann_tattoo/ lo fa lei") == "@ann_tattoo"
    assert estrai_handle("scrivimi a matteo@gmail.com") == ""      # email, non handle
    assert estrai_handle("nessun artista qui") == ""


def test_handle_vicino_non_ruba_lartista_del_messaggio_prima():
    """REGRESSIONE misurata dal vivo: con due foto di due tatuatori nella stessa chat,
    «primo handle della finestra» attribuiva a ciascuna l'artista dell'altra."""
    msgs = parse_export(DUE_ARTISTI)
    i1 = next(i for i, m in enumerate(msgs) if m.allegato == "FOTO-1.jpg")
    i2 = next(i for i, m in enumerate(msgs) if m.allegato == "FOTO-2.jpg")
    assert handle_vicino(msgs, i1) == "@dario.ink"
    assert handle_vicino(msgs, i2) == "@ann_tattoo"     # prima diceva @dario.ink


def test_handle_nella_didascalia_vince_sui_vicini():
    msgs = parse_export(
        "[01/01/24, 10:00:00] X: prima si parlava di @altro.tizio\n"
        "[01/01/24, 10:01:00] X: ‎<allegato: F.jpg> di @giusto.ink\n")
    assert handle_vicino(msgs, 1) == "@giusto.ink"


def test_nessun_handle_resta_vuoto_non_inventato():
    msgs = parse_export("[01/01/24, 10:00:00] X: ‎<allegato: F.jpg>\n")
    assert handle_vicino(msgs, 0) == ""


def test_contesto_toglie_i_nomi_file_e_taglia():
    msgs = parse_export(IOS)
    ctx = contesto(msgs, 1)
    assert "Guarda che roba" in ctx and "@dario.ink" in ctx
    assert "00000042-PHOTO" not in ctx        # il nome file è rumore, non contesto
    assert len(ctx) <= MAX_CONTESTO


def test_fetch_ios_produce_provenance_e_artista(tmp_path):
    d = _scrivi_export(tmp_path / "Tatuaggi mab", IOS,
                       immagini=["00000042-PHOTO-2024-09-06-21-14-20.jpg"])
    items = list(WhatsAppAdapter().fetch(SourceRef(kind="whatsapp", ref=str(d))))
    assert len(items) == 1
    it = items[0]
    assert it.artist_handle == "@dario.ink"                 # dedotto dal messaggio accanto
    assert it.license_note == "whatsapp-personal"
    assert it.source_url == "whatsapp://Tatuaggi mab/00000042-PHOTO-2024-09-06-21-14-20.jpg"
    assert Path(it.local_path).is_file()
    assert it.meta["chat"] == "Tatuaggi mab"
    assert "Guarda che roba" in it.meta["contesto"]


def test_fetch_android_con_txt_dal_nome_diverso(tmp_path):
    d = _scrivi_export(tmp_path / "coppia", ANDROID, nome="WhatsApp Chat with Giulia.txt",
                       immagini=["IMG-20240112-WA0007.jpg"])
    items = list(WhatsAppAdapter().fetch(SourceRef(kind="whatsapp", ref=str(d))))
    assert len(items) == 1 and items[0].artist_handle == "@ann_tattoo"


def test_allegato_mancante_viene_saltato_non_inventato(tmp_path):
    """Export «senza media»: la riga c'è, il file no. Meglio zero item che un path finto."""
    d = _scrivi_export(tmp_path / "senza-media", IOS)      # nessuna immagine sul disco
    assert list(WhatsAppAdapter().fetch(SourceRef(kind="whatsapp", ref=str(d)))) == []


def test_cartella_senza_export_non_esplode(tmp_path):
    vuota = tmp_path / "vuota"
    vuota.mkdir()
    assert list(WhatsAppAdapter().fetch(SourceRef(kind="whatsapp", ref=str(vuota)))) == []
    assert trova_export(vuota) is None


def test_privacy_il_contesto_e_troncato():
    """La chat NON si copia: per ogni immagine resta un indizio corto, non il dialogo."""
    lungo = "\n".join(f"[01/01/24, 10:0{i%10}:00] Tizio: messaggio lunghissimo {'x' * 200}"
                      for i in range(10))
    msgs = parse_export(lungo)
    assert len(contesto(msgs, 5, finestra=4)) <= MAX_CONTESTO


def test_export_preferisce_chat_txt(tmp_path):
    d = tmp_path / "mix"
    d.mkdir()
    (d / "altro.txt").write_text("x", encoding="utf-8")
    (d / "_chat.txt").write_text(IOS, encoding="utf-8")
    assert trova_export(d).name == "_chat.txt"


def test_due_artisti_nella_stessa_chat_non_si_confondono():
    """Caso reale (chat «Tatuaggi di coppia»): due reference di due tatuatori diversi.
    Con la finestra simmetrica cieca la seconda foto ereditava l'handle della prima."""
    msgs = parse_export(
        "[12/03/24, 21:14:02] Matteo: guarda questo\n"
        "[12/03/24, 21:14:08] Matteo: <allegato: a.jpg>\n"
        "[12/03/24, 21:15:30] Matteo: e' di @sara.ink.studio, sta a Pisa\n"
        "[12/03/24, 21:16:02] Jessica: bello! anche questo\n"
        "[12/03/24, 21:16:20] Jessica: <allegato: b.jpg>\n"
        "[12/03/24, 21:16:44] Jessica: https://instagram.com/marco_fineline_ ha fatto questo\n"
    )
    prima, seconda = (k for k, m in enumerate(msgs) if m.allegato)
    assert estrai_handle(contesto(msgs, prima)) == "@sara.ink.studio"
    assert estrai_handle(contesto(msgs, seconda)) == "@marco_fineline_"


def test_i_link_a_contenuti_instagram_non_sono_artisti():
    """DIFETTO MISURATO sulle chat vere (25/07): `instagram.com/reel/XYZ` è un contenuto
    CONDIVISO, non un profilo — la regex ne prendeva il primo segmento e attribuiva
    **18 immagini** a un tatuatore inesistente «@reel». Da un link a un contenuto l'autore
    non è deducibile: meglio nessun artista che uno inventato (guardia §11.4)."""
    for url in ("https://www.instagram.com/reel/DAbc123/",
                "https://instagram.com/p/CXYZ/",
                "https://www.instagram.com/tv/Babc/",
                "https://instagram.com/stories/qualcuno/123"):
        assert estrai_handle(url) == "", url
    # un profilo vero continua a funzionare
    assert estrai_handle("https://instagram.com/ann_tattoo/") == "@ann_tattoo"
