# NEXT — ink-scout
> Aggiornato: 2026-07-09 · La storia completa vive in docs/2026-07-04-ink-scout-design.md

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
- [x] Scrivere il piano di implementazione (writing-plans) dallo spec approvato — **FATTO 23/07**: `docs/plans/2026-07-23-ink-scout-mvp.md` (23 task TDD, 7 fasi, ~3250 righe; copre tutto lo scope §13; self-review vs spec inclusa)
- [ ] Implementare l'MVP v1 eseguendo il piano `docs/plans/2026-07-23-ink-scout-mvp.md` (subagent-driven o executing-plans). Milestone camminante dopo la Fase 4 (upload → libreria → Modo E → export). Debito noto: SVG centerline (`autotrace`) rimandato post-v1, l'MVP usa vtracer.

## Backlog
- Post-v1 (spec §13 «Dopo»): Modo B locale GPU, Modo C avanzato (ControlNet/IP-adapter), adapter Pinterest/Tattoodo, refine inpainting + storico versioni ricco, embedding semantico temi su larga scala
- Decidere provider API secondario dopo fal.ai (Gemini vs Stability/Replicate) solo quando/se serve — l'interfaccia lo supporta già (spec §15)
- Validare con un legale IP prima di qualsiasi uso commerciale (spec §11.9)
- Rifinire il vocabolario stili iniziale di `data/styles.seed.yaml` (dalla tassonomia della ricerca) in fase di piano (spec §15)

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
