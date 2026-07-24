# NEXT — ink-scout
> Aggiornato: 2026-07-24 · La storia completa vive in docs/2026-07-04-ink-scout-design.md

<!-- BEGIN conoscenza 2026-07-23 -->
## Conoscenza — quali corsi servono a questo

> Da `atlante domanda` (modello **locale**, costo API zero), rigenerato il 2026-07-23.
> ⚠️ **Proposte** del modello, non confermate: il legame progetto→corso è un giudizio.

| corso | perché (tema in comune) |
|---|---|
| `archivio-live` | computer vision |
| `computer-vision` | computer vision |
| `hacker-dellia` | computer vision |
| `video-esclusivi` | computer vision |

Per interrogarli: `uv run atlante ask "<domanda>"` in `atlante-ia`, o il server MCP
`atlante-ia` (`search`, `get_note`) da qualsiasi progetto — vedi `CLAUDE.md` §8.
<!-- END conoscenza 2026-07-23 -->


## Ora (max 3)
- [x] ~~Implementare l'MVP v1 eseguendo il piano~~ — **FATTO 24/07, 23/23 task**: pipeline subagent-driven (ondate di 2-3 Sonnet in parallelo, review Fable tra le ondate), 78 test + 1 skip (vtracer), ruff pulito, 27 commit. Milestone camminante verificata dal vivo (upload→libreria con dedup reale→Modo E→stencil 300 DPI) + test integrazione e2e offline. Guardie §11 testate a livello di pixel/HTML. Debito noto invariato: SVG centerline (`autotrace`) post-v1, l'MVP usa vtracer.
- [ ] **Provarlo su immagini vere di Matteo**: `uv run ink-scout sync-styles && uv run ink-scout ingest --kind upload --ref <cartella reference>` poi `serve` — il flusso è verificato con immagini sintetiche, non col suo materiale.
- [ ] Installare l'extra `[tag]` e verificare ClipTagger su hardware reale (M3 Pro): oggi il tagging CLIP è coperto solo da encoder iniettato nei test.
- [ ] (Opzionale, costa centesimi) Modo A live: key fal.ai nel Keychain (`security add-generic-password -a inkscout-fal-key -s ink-scout -w`) e 1 generazione vera.

## Backlog
- Post-v1 (spec §13 «Dopo»): Modo B locale GPU, Modo C avanzato (ControlNet/IP-adapter), adapter Pinterest/Tattoodo, refine inpainting + storico versioni ricco, embedding semantico temi su larga scala
- Decidere provider API secondario dopo fal.ai (Gemini vs Stability/Replicate) solo quando/se serve — l'interfaccia lo supporta già (spec §15)
- Validare con un legale IP prima di qualsiasi uso commerciale (spec §11.9)
- Rifinire il vocabolario stili iniziale di `data/styles.seed.yaml` (dalla tassonomia della ricerca) (spec §15)
- **Osservazioni dall'implementazione 24/07** (dagli esecutori, da valutare):
  - `sync_styles` è idempotente ma non propaga: editare `styles.seed.yaml` dopo il primo sync non aggiorna i campi degli stili già in DB (solo nomi nuovi)
  - portare il mapping line_treatment (`_BOLD`/`_FINE` in `ideation/brief.py`, oggi nomi di stile nel codice) nei `formal_attributes` del seed YAML
  - `engine/hosted.py`: nome file da `hash()` Python (instabile tra run) → passare a sha256 dell'URL/contenuto
  - `ingest/site.py`: JSON-LD via regex semplice → `json.loads` mirato sui blocchi `<script type="application/ld+json">`
  - ingest: i Global Constraints citano «throttle + backoff» ma il contratto implementa solo il throttle (e scatta per item emesso, non per richiesta HTTP — rilevante se si pagina)
  - web: CTA/attribuzione condizionate a `handle` non vuoto; valutare `artist.provenance_url` come link canonico della CTA al posto del `source_url` dell'immagine

## Idee


<!-- BEGIN wa-idee 2026-07-12 -->
### 💬 Da WhatsApp (2026-07-12)
- 💡 Aggiungere ai risultati del generatore un output "tatuaggio temporaneo" (mockup/prova indossabile prima di farlo definitivo) — *«Cose da comprare»* `[14/06/23]`
- 💡 Supportare tatuaggi a scritta/lettering: selezione di font e stili calligrafici per generare soggetti testuali — *«Tatuaggi mab»* `[06/09/24]`
- 💡 Modulo "trova tatuatore": suggerire studi/artisti in base allo stile scelto, sul modello delle guide di settore per categoria — *«Tatuaggi mab»* `[12/01/24]`
- 💡 Sezione aftercare nell'app: checklist/promemoria di cura post-seduta collegata al soggetto scelto — *«Tatuaggi coppia»* `[03/08/24]`
<!-- END wa-idee 2026-07-12 -->


<!-- BEGIN wa-idee 2026-07-16b -->
### 💬 Da WhatsApp — «Cose da ricordare» (estrazione profonda, 16/07/26)
- 💡 Valutare un motore/backend di generazione immagini stile Ideogram per produrre scritte/lettering in stili grafici specifici come spunto per il generatore di tatuaggi (es. scritta "stile Kafka") — *«quaderno Cose da ricordare»* `[30/10/24]`
<!-- END wa-idee 2026-07-16b -->

## Deciso di non fare
- Scraping come feature-da-servizio: harvest solo personale opt-in (spec §11.3)
- Training/LoRA su opere scrapate; niente prompt «in the style of [artista vivente]» (spec §11.2, §11.8)
- Framework web pesante: web via stdlib; dipendenze pesanti dietro extras (spec §12)
