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
- [x] ~~Verificare ClipTagger su hardware reale~~ — **FATTO 24/07**: extra `[tag]` installato (torch 2.13, MPS disponibile), pesi veri ViT-B-32, ~1,4 s/immagine dopo il warm-up. Trovato e corretto un **mismatch QuickGELU silenzioso** (`ViT-B-32` + pesi `openai` degrada l'accuratezza: ora `ViT-B-32-quickgelu`). ⚠️ Con soglia 0,20 su forme geometriche sintetiche **nessuno stile supera la soglia** (punteggi ~0,10 tutti appiattiti): la soglia va ritarata su immagini vere, non su disegni finti.
- [x] ~~Verificare la web UI nel browser~~ — **FATTO 24/07**: galleria, studio, generate (Modo E) e export stencil provati dal vivo su dati demo. Guardie §11 confermate a schermo (banner, attribuzione, CTA, `do_not_mimic` filtrato). Corretti due difetti visti solo così: handle con **doppia chiocciola** (`@@jane`) e attribuzione sbagliata con più artisti nella stessa chat.
- [x] ~~Debiti tecnici + tagging senza modelli~~ — **FATTO 25/07** (111 test, ruff pulito):
  **(a)** `TestoTagger` — i tag vengono dalle **parole scritte in chat** (stile, forma, colore,
  placement, soggetto), senza GPU/API/CLIP: è deterministico, spiegabile, e **funziona proprio dove
  CLIP tace** (vedi la soglia 0,20 qui sopra). Il soggetto resta testo libero → la galleria è
  cercabile con le parole di Matteo («serpente» ritrova la sua foto). Agganciato all'ingest.
  **(b)** vocabolario degli **assi** (`form/color_mode/placement/density`) nel seed, coi modi in cui
  li scrive in italiano («rotondo»→`round`, «polso»→`wrist`).
  **(c)** chiusa la violazione del vincolo §2 (vedi Backlog), `sync_styles` che non propagava,
  e il nome-file instabile di `hosted.py`.
- [x] ~~**Provarlo sul materiale VERO**~~ — **FATTO 25/07**, e non serviva esportare niente: gli
  export delle due chat erano già in `~/.claude-whatsapp/exports-archive/` (**147 immagini**,
  formato iOS). Ingerite → **124 uniche** (23 collassate dal dedup pHash, incluse quelle mandate
  in entrambe le chat). **Tre difetti che solo i dati veri potevano rivelare:**
  1. 🐛 **CLIP non discriminava nulla** — e non era colpa delle immagini sintetiche, come si
     era supposto il 24/07: mancava **`logit_scale`** prima della softmax. Misurato su 40
     reference vere: prima min 0,101 · mediana 0,103 · max 0,105 (l'uniforme su 10 stili è
     0,100!), dopo **0,252 / 0,428 / 0,914**. Soglia default 0,20 → **0,30** (copertura 87%).
  2. 🐛 **18 immagini attribuite a «@reel»**, un tatuatore inesistente: `instagram.com/reel/…`
     è un contenuto condiviso, non un profilo. Ora i segmenti di percorso IG sono esclusi.
  3. 🐛 **Frasi intime della chat di coppia finite nei tag `subject`** → il soggetto si salva
     solo se il contesto parla davvero di tatuaggi (`pertinente()`).
  **Cosa dicono i numeri sul materiale**: solo il **29%** degli allegati ha del testo accanto, e
  quel testo parla per lo più di **aftercare e logistica dello studio**, non di stili → il canale
  di tagging principale qui è **CLIP** (`ink-scout tag`), non il testo. E i link IG puntano a
  reel/post, non a profili: **il tatuatore raramente è deducibile** dalla chat.
- [ ] **L'unica cosa che serve il tuo occhio**: aprire `ink-scout serve` e guardare 15-20 immagini
  con lo stile che CLIP ha assegnato, dicendo se è giusto. La soglia 0,30 è tarata sulla
  **copertura** (87%), **non sulla precisione**: quella non la può misurare un numero. Se sbaglia
  spesso, le leve sono due — alzare la soglia, o riscrivere i prompt del vocabolario stili
  (oggi `"a {stile} tattoo"`, che è il default ingenuo di CLIP).
- [ ] (Opzionale, costa centesimi) Modo A live: key fal.ai nel Keychain (`security add-generic-password -a inkscout-fal-key -s ink-scout -w`) e 1 generazione vera.

## Backlog
- Post-v1 (spec §13 «Dopo»): Modo B locale GPU, Modo C avanzato (ControlNet/IP-adapter), adapter Pinterest/Tattoodo, refine inpainting + storico versioni ricco, embedding semantico temi su larga scala
- Decidere provider API secondario dopo fal.ai (Gemini vs Stability/Replicate) solo quando/se serve — l'interfaccia lo supporta già (spec §15)
- Validare con un legale IP prima di qualsiasi uso commerciale (spec §11.9)
- Rifinire il vocabolario stili iniziale di `data/styles.seed.yaml` (dalla tassonomia della ricerca) (spec §15)
- **Osservazioni dall'implementazione 24/07** (dagli esecutori, da valutare):
  - ✅ ~~`sync_styles` è idempotente ma non propaga~~ — **chiuso 25/07**: `upsert_style` fa UPDATE dei campi; test che modifica il seed e verifica la propagazione
  - ✅ ~~portare il mapping line_treatment (`_BOLD`/`_FINE`, nomi di stile nel codice) nei dati~~ — **chiuso 25/07**: tabella `line_treatments` nel seed (**l'ordine è la priorità**), il codice conosce solo l'asse `linework`. Due guardie: un test fallisce se un nome di stile torna nel sorgente, un altro prova che uno stile *inventato* nel solo seed funziona senza toccare Python
  - **ritarare la soglia di ClipTagger** (oggi 0,20) su reference vere: sulle forme sintetiche i punteggi restano tutti ~0,10 e nessun tag passa — *nel frattempo il `TestoTagger` copre il caso «immagine con didascalia»*
  - ✅ ~~`engine/hosted.py`: nome file da `hash()` Python (instabile tra run)~~ — **chiuso 25/07**: sha256 del **contenuto**, così due generazioni identiche collassano su un file solo
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
