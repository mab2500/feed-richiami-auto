# NEXT — ink-scout
> Aggiornato: 2026-07-09 · La storia completa vive in docs/2026-07-04-ink-scout-design.md

<!-- BEGIN conoscenza 2026-07-21 -->
## Conoscenza — quali corsi servono a questo

> Da `atlante domanda` (modello **locale**, costo API zero) e **filtrati**: dei 277 legami
> proposti sull'intero portafoglio ne sono stati scritti **68**, cioè solo quelli in cui
> **tutte** le parole del tema compaiono davvero fra i `temi`/`strumenti` delle note di quel
> corso. Scartati: 101 parziali, 19 deboli e **89 che puntavano a corsi non ancora
> distillati** — lì il modello aveva giudicato dal titolo, non dal contenuto.
> Restano **proposte verificate contro il vault**, non un giudizio di Matteo.

| corso | perché (tema in comune) |
|---|---|
| `computer-vision` | computer vision |
| `hacker-dellia` | computer vision |
| `video-esclusivi` | computer vision |

Per interrogarli: `uv run atlante ask "<domanda>"` dentro `atlante-ia`, oppure il server MCP
`atlante-ia` (`search`, `get_note`) da qualsiasi progetto — vedi `CLAUDE.md` §8.
<!-- END conoscenza 2026-07-21 -->

## Ora (max 3)
- [ ] Scrivere il piano di implementazione (writing-plans) dallo spec approvato — «Nessun blocco: si può procedere a writing-plans» (spec §15)
- [ ] Implementare l'MVP v1 secondo lo scope dello spec §13 (ingest upload/siti/IG opt-in, libreria+dedup pHash, ClipTagger, web UI galleria, brief, Modo E + Modo A opt-in, export 300 DPI+SVG, guardie §11, test)

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
