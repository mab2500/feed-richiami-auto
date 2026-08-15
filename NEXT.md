# NEXT — ink-scout
> Aggiornato: 2026-08-15 · La storia completa vive in docs/2026-07-04-ink-scout-design.md

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
- [x] ~~Implementare l'MVP v1 eseguendo il piano~~ — **FATTO 15/08, 23/23 task**: pipeline subagent-driven (ondate di 2-3 Sonnet in parallelo, review Fable tra le ondate), 78 test + 1 skip (vtracer), ruff pulito, 27 commit. Milestone camminante verificata dal vivo (upload→libreria con dedup reale→Modo E→stencil 300 DPI) + test integrazione e2e offline. Guardie §11 testate a livello di pixel/HTML. Debito noto invariato: SVG centerline (`autotrace`) post-v1, l'MVP usa vtracer.
- [x] ~~Verificare ClipTagger su hardware reale~~ — **FATTO 15/08**: extra `[tag]` installato (torch 2.13, MPS disponibile), pesi veri ViT-B-32, ~1,4 s/immagine dopo il warm-up. Trovato e corretto un **mismatch QuickGELU silenzioso** (`ViT-B-32` + pesi `openai` degrada l'accuratezza: ora `ViT-B-32-quickgelu`). ⚠️ Con soglia 0,20 su forme geometriche sintetiche **nessuno stile supera la soglia** (punteggi ~0,10 tutti appiattiti): la soglia va ritarata su immagini vere, non su disegni finti.
- [x] ~~Verificare la web UI nel browser~~ — **FATTO 15/08**: galleria, studio, generate (Modo E) e export stencil provati dal vivo su dati demo. Guardie §11 confermate a schermo (banner, attribuzione, CTA, `do_not_mimic` filtrato). Corretti due difetti visti solo così: handle con **doppia chiocciola** (`@@jane`) e attribuzione sbagliata con più artisti nella stessa chat.
- [x] ~~Debiti tecnici + tagging senza modelli~~ — **FATTO 15/08** (111 test, ruff pulito):
  **(a)** `TestoTagger` — i tag vengono dalle **parole scritte in chat** (stile, forma, colore,
  placement, soggetto), senza GPU/API/CLIP: è deterministico, spiegabile, e **funziona proprio dove
  CLIP tace** (vedi la soglia 0,20 qui sopra). Il soggetto resta testo libero → la galleria è
  cercabile con le parole di Matteo («serpente» ritrova la sua foto). Agganciato all'ingest.
  **(b)** vocabolario degli **assi** (`form/color_mode/placement/density`) nel seed, coi modi in cui
  li scrive in italiano («rotondo»→`round`, «polso»→`wrist`).
  **(c)** chiusa la violazione del vincolo §2 (vedi Backlog), `sync_styles` che non propagava,
  e il nome-file instabile di `hosted.py`.
- [x] ~~**Provarlo sul materiale VERO**~~ — **FATTO 15/08**, e non serviva esportare niente: gli
  export delle due chat erano già in `~/.claude-whatsapp/exports-archive/` (**147 immagini**,
  formato iOS). Ingerite → **124 uniche** (23 collassate dal dedup pHash, incluse quelle mandate
  in entrambe le chat). **Tre difetti che solo i dati veri potevano rivelare:**
  1. 🐛 **CLIP non discriminava nulla** — e non era colpa delle immagini sintetiche, come si
     era supposto prima (15/08, su immagini sintetiche): mancava **`logit_scale`** prima della softmax. Misurato su 40
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
  - ⏸ rimandato **[29/07]** (rimanda)  <!-- plancia:nex-abdb15fc01 -->
  con lo stile che CLIP ha assegnato, dicendo se è giusto. La soglia 0,30 è tarata sulla
  **copertura** (87%), **non sulla precisione**: quella non la può misurare un numero. Se sbaglia
  spesso, le leve sono due — alzare la soglia, o riscrivere i prompt del vocabolario stili
  (oggi `"a {stile} tattoo"`, che è il default ingenuo di CLIP).
- [ ] (Opzionale, costa centesimi) Modo A live: key fal.ai nel Keychain (`security add-generic-password -a inkscout-fal-key -s ink-scout -w`) e 1 generazione vera.
  - ✅ deciso **[29/07]** No, rimandare a fase successiva Evita spese anche se piccole.  <!-- plancia:dom-96ba3e744b -->

## Backlog
- Post-v1 (spec §13 «Dopo»): Modo B locale GPU, Modo C avanzato (ControlNet/IP-adapter), adapter Pinterest/Tattoodo, refine inpainting + storico versioni ricco, embedding semantico temi su larga scala
- Decidere provider API secondario dopo fal.ai (Gemini vs Stability/Replicate) solo quando/se serve — l'interfaccia lo supporta già (spec §15)
- Validare con un legale IP prima di qualsiasi uso commerciale (spec §11.9)
- Rifinire il vocabolario stili iniziale di `data/styles.seed.yaml` (dalla tassonomia della ricerca) (spec §15)
- **Osservazioni dall'implementazione 15/08** (dagli esecutori, da valutare):
  - ✅ ~~`sync_styles` è idempotente ma non propaga~~ — **chiuso 15/08**: `upsert_style` fa UPDATE dei campi; test che modifica il seed e verifica la propagazione
  - ✅ ~~portare il mapping line_treatment (`_BOLD`/`_FINE`, nomi di stile nel codice) nei dati~~ — **chiuso 15/08**: tabella `line_treatments` nel seed (**l'ordine è la priorità**), il codice conosce solo l'asse `linework`. Due guardie: un test fallisce se un nome di stile torna nel sorgente, un altro prova che uno stile *inventato* nel solo seed funziona senza toccare Python
  - ✅ ~~ritarare la soglia di ClipTagger (0,20): sulle forme sintetiche nessun tag passa~~ — **voce SBAGLIATA, chiusa il 15/08**: la soglia non c'entrava, mancava `logit_scale` prima della softmax (vedi «Ora» sopra). Diagnosi corretta solo dai dati veri; soglia ora 0,30
  - ✅ ~~`engine/hosted.py`: nome file da `hash()` Python (instabile tra run)~~ — **chiuso 15/08**: sha256 del **contenuto**, così due generazioni identiche collassano su un file solo
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

### 📡 Proposte dal radar ricerca-AI — da confermare
<!-- radar-ricerca-ai:blocco-idee — generato da `radar dispatch`; i marcatori `radar-idea:` evitano i doppioni, non toglierli -->
> ⚠️ Voci proposte dal radar a partire dalla ricerca AI: **non sono decisioni di Matteo**.
> Si confermano, si riscrivono o si cancellano a mano — il radar non le rimette.

- 💡 **Candidare Mage-Flow come backend locale/self-hosted del motore generativo pluggable, per generare reference e stencil a risoluzione nativa 1024x1024 invece di generare basso e upscalare.** — ⚠️ *proposta del radar, non confermata* <!-- radar-idea:1ec7c0b30e -->
  come: ink-scout ha per design un motore PLUGGABLE default-offline con fal.ai solo opt-in, e l'MVP è appena chiuso (78 test, prossimo passo: provarlo su immagini vere). Il meccanismo di Mage-Flow — co-design tokenizer+backbone che permette training/inferenza a risoluzione nativa con un modello da soli 4B e latenza <1s su A100 — è esattamente il profilo che serve al backend offline: 4B è l'ordine di grandezza che (quantizzato) può stare nei 18 GB dell'M3 Pro, e la risoluzione nativa evita l'upscaling che sporca le linee pulite richieste dall'export stencil. In più la capacità di EDITING coprirebbe il caso d'uso 'reference reale → variazione nello stile X' con un solo modello, senza pipeline img2img separata. Passo concreto: aggiungere un adapter nel motore pluggable e un check di fattibilità (pesi disponibili? gira su MPS/Metal?). Confidence bassa perché la riproducibilità è 'non dichiarato': senza pesi pubblici resta carta.
  ↳ 2026-07-26 · da `radar-ricerca-ai` (motore idee) · lavoro: «Mage-Flow: An Efficient Native-Resolution Foundation Model for Image Generation and Editing» https://huggingface.co/papers/2607.19064 · sforzo M · confidenza 0.40

## Deciso di non fare
- Scraping come feature-da-servizio: harvest solo personale opt-in (spec §11.3)
- Training/LoRA su opere scrapate; niente prompt «in the style of [artista vivente]» (spec §11.2, §11.8)
- Framework web pesante: web via stdlib; dipendenze pesanti dietro extras (spec §12)
