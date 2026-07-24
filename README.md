# ink-scout

Strumento **locale** per ideare, generare e rifinire il disegno da farsi tatuare, partendo dal lavoro dei tatuatori che ti ispirano.

Dai delle **fonti** (tue immagini, siti personali di tatuatori, o harvest personale opt-in da Instagram/Pinterest) → `ink-scout` **raccoglie e indicizza** il loro lavoro in una libreria sfogliabile e filtrabile → da lì **ideazione + generazione** di un disegno, da una reference esistente **oppure** da un tema libero (es. *"qualcosa di rotondo a tema Twin Peaks"*), fino a un **export stencil** pronto da portare dal tatuatore.

## Stato

🟢 **Flusso MVP offline implementato e verificato end-to-end** (upload → libreria → tag → brief → Modo E → export stencil → web UI in-process, senza rete — vedi `tests/test_integration.py`). CLIP, export SVG, fallback CDP e Modo A (fal.ai) restano dietro extra opzionali.
Vedi: [`docs/2026-07-04-ink-scout-design.md`](docs/2026-07-04-ink-scout-design.md) per lo spec completo.

## Quickstart (MVP offline)

```bash
uv sync
uv run ink-scout sync-styles                          # popola il vocabolario stili
uv run ink-scout ingest --kind upload --ref ./le-mie-immagini
uv run ink-scout serve                                # http://127.0.0.1:8765
```

- **Modo E (default):** offline, nessuna chiave — produce brief + moodboard + prompt pronto.
- **Modo A (opt-in):** salva la key fal.ai nel Keychain e imposta il model-id:
  ```bash
  security add-generic-password -a inkscout-fal-key -s ink-scout -w
  export INK_SCOUT_FAL_MODEL_ID=fal-ai/flux/schnell
  ```
- **Extra pesanti opzionali:** `uv pip install -e ".[tag]"` (CLIP), `".[export]"` (SVG vtracer), `".[cdp]"` (fallback browser).

Ogni output è marcato **"AI-generated / reference only"**: ink-scout serve a preparare un reference da portare a un tatuatore umano.

## Idee portanti

- **Motore d'ispirazione + generatore** in un unico flusso.
- **Zero hardcoding** di temi / artisti / stili: sono *dati*. Stile ≠ tema (assi ortogonali).
- **Generazione pluggable**: default offline (brief + moodboard + prompt pronto), API cloud (fal.ai/Flux) opt-in dietro adapter, motore locale GPU predisposto.
- **Stile "alla X" via reference reali** (condiziona sulle immagini raccolte + descrittori neutri), **mai** `"in the style of [nome]"` nei prompt.
- **Stack "casa"**: Python moderno (uv/ruff/pytest), web UI stdlib, scraper HTTP-first + fallback CDP, cache su disco, SQLite (WAL), provenance su ogni dato.

## Etica / IP (non opzionale)

`ink-scout` è pensato come **moodboard/reference privato → poi commissioni un tatuatore umano**, non come "stampa il tuo tatuaggio finito". Attribuzione all'artista, CTA "commissiona questo artista", output marcato *AI / reference only*, opt-out artisti, niente scraping come servizio, niente training su opere scrapate. Uso personale. Per usi commerciali serve validazione legale IP (UE/Italia: copyright + GDPR). Dettagli in §11 dello spec.

## Licenza

Privato / uso personale.
