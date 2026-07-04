# ink-scout — Design / Spec

- **Data:** 2026-07-04
- **Stato:** approvato in brainstorming, in attesa di review dello spec → poi writing-plans
- **Autore:** Matteo (+ Claude)
- **Repo previsto:** privato, `github.com/mab2500/ink-scout` (da creare)

---

## 1. Visione (una frase)

Uno strumento locale che, date delle **fonti** (tuoi upload, siti personali di tatuatori, o harvest personale opt-in da Instagram/Pinterest), **raccoglie e indicizza** il loro lavoro in una libreria sfogliabile, e da lì ti aiuta a **ideare, generare e rifinire** il disegno da farti tatuare — partendo da una reference esistente **oppure** da un tema libero (es. *"qualcosa di rotondo e bello a tema Twin Peaks"*), fino a un **export stencil** pronto da portare dal tatuatore.

Due pilastri:

1. **Motore d'ispirazione** — ingest → libreria + dedup → tagging stile/soggetto/forma/colore → galleria sfogliabile/filtrabile → preferiti.
2. **Generatore** — brief strutturato → motore di generazione **pluggable** → iterazione sulle modifiche → export stencil.

**Caso studio guida (NON hardcodato):** "rotondo + Twin Peaks" è semplicemente `forma=round` + `tema="Twin Peaks"` (testo libero) risolto a runtime. Nessun tema/artista/stile è cablato nel codice.

---

## 2. Principi di progetto (vincoli non negoziabili)

- **Zero hardcoding di temi, artisti, stili.** Sono **dati**, non `enum` nel codice. Il codice conosce *assi* (stile, forma, colore, ecc.), non *valori* (Twin Peaks, Dr. Woo, cybersigilism).
- **Stile ≠ tema.** Assi ortogonali: lo **stile** è il *come* (linee, contrasto, palette, tecnica) ed è un vocabolario estendibile via dati; il **tema/soggetto** è il *cosa* ed è **campo aperto** (testo libero + embedding), mai enum.
- **Generazione pluggable.** Un solo contratto `DesignEngine`, N backend selezionabili. Nessun `if provider == "flux"` sparso. Model-id e prezzi in config, mai nel sorgente.
- **Motore pesante sempre opzionale.** L'MVP funziona offline, senza GPU, senza chiavi. GPU e API sono upgrade.
- **Guardie etiche/IP visibili nel prodotto** (vedi §11). Framing = *reference privato → commissioni un tatuatore umano*, non *"stampa il tuo tatuaggio finito"*.
- **Stile "casa":** Python moderno (uv/ruff/pytest), web UI locale stdlib, scraper **HTTP-first + fallback CDP**, **cache su disco**, **SQLite WAL**, provenance su ogni dato, test. Coerente con `pricehunt`/`viaggio-advisor`/`cosa-guardo`.

---

## 3. Decisioni chiave (locked)

| # | Decisione | Scelta | Motivazione |
|---|---|---|---|
| D1 | Cuore del tool | **Motore d'ispirazione + generatore** | Copre l'intero flusso descritto: raccogli → sfogli → ideazione → disegno |
| D2 | Backend generazione MVP | **Default E (brief+moodboard+prompt) + API cloud opt-in (fal.ai) dietro adapter** | Spedibile day-one, zero costi/chiavi; motore reale attivabile con una key |
| D3 | Stile "alla X" | **Vibe via reference reali** (image-conditioning su portfolio raccolto + descrittori neutri) | Più fedele di un nome nel prompt; evita blocchi API e il punto caldo legale/community |
| D4 | Ingest | **Upload + siti personali + harvest IG/Pinterest opt-in personale** (throttle+cache, uso privato, no ridistribuzione) | Copre il caso d'uso restando difendibile; scraping non è una "feature da servizio" |
| D5 | Modello dati | **Style = tabella estendibile con gerarchia/tag; Subject/Theme = testo libero + embedding; Artist = seed+ingestion+provenance** | Niente invecchiamento, gestisce temi arbitrari, separa stile da tema |
| D6 | Motore locale GPU | **Rimandato** (adapter predisposto) | Matteo è su Mac (MPS fragile per ControlNet); si aggiunge se/quando c'è una NVIDIA ~16GB |

---

## 4. Architettura a moduli

Ogni modulo ha una responsabilità unica, un'interfaccia chiara, è testabile in isolamento.

```
┌──────────────────────────────────────────────────────────────────┐
│  WEB UI locale (7)                                                 │
│  Brief builder · Moodboard · Galleria filtrabile · Studio genera  │
│  · Iterazione · Export                                            │
└───────────────┬──────────────────────────────────────────────────┘
                │  (http locale, stdlib)
   ┌────────────┼────────────┬───────────────┬──────────────┐
   ▼            ▼            ▼               ▼              ▼
[1 INGEST]  [2 LIBRERIA]  [3 TAGGING]   [4 IDEAZIONE]   [6 EXPORT]
 SourceAdapter  SQLite+dedup  stile/tag    Brief→Engine   stencil
 HTTP-first     provenance                     │          300DPI/SVG
 +CDP cache                               [5 REFINE]
                                          varianti/edit
```

### Modulo 1 — Ingest / scraper (`inkscout.ingest`)
- **Responsabilità:** dato un input (file upload, URL sito, handle IG/Pinterest), produrre una lista di immagini + metadati grezzi in cache.
- **Interfaccia:** `SourceAdapter.fetch(source: SourceRef) -> Iterable[RawItem]`. Un adapter per tipo: `UploadAdapter`, `PersonalSiteAdapter`, `InstagramAdapter`, `PinterestAdapter`, `TattoodoAdapter`.
- **Strategia:** **HTTP-first** con `curl_cffi` (impersona TLS/JA3 di Chrome) → **fallback CDP** (`nodriver`/Camoufox) SOLO per JS-heavy/anti-bot. **Cache su disco** di HTML/JSON e immagini. Rate-limit gentile (backoff 10–15 min, throttle) sul modo harvest.
- **Ordine di lecità/facilità:** (a) upload utente, (b) sito personale (og:image/sitemap/JSON-LD — facile e lecito), (c) IG/Pinterest **solo modo harvest personale opt-in** con banner di rischio ToS.
- **Provenance:** ogni `RawItem` porta `source_url`, `artist_handle`, `fetched_at`, `license_note`.

### Modulo 2 — Libreria + dedup (`inkscout.library`)
- **Responsabilità:** persistere immagini + metadati, collassare duplicati/near-dup, gestire preferiti e "non mi interessa".
- **Storage:** SQLite (WAL). Immagini su filesystem (`data/images/…`), riga DB con path + hash.
- **Dedup:** **hash percettivo** (pHash/dHash) per collassare duplicati e near-dup; segnala anche potenziali "copia 1:1" in fase di export (guardia IP).
- **Provenance obbligatoria** su ogni immagine (fonte, autore, URL, licenza nota).

### Modulo 3 — Tagging / stile (`inkscout.tagging`)
- **Responsabilità:** derivare per-immagine `{style[], subject[], body_placement, color_mode, density, form}`.
- **Backend pluggable:** `Tagger` protocol. **(a) `ClipTagger`** — CLIP zero-shot locale su vocabolario stili (default: gratis, batch, offline-ish). **(b) `VisionLLMTagger`** — Vision LLM (Claude) per casi sfumati / descrizioni libere.
- **Vocabolario stili** caricato da **seed file YAML editabile** (`data/styles.seed.yaml`), MAI enum nel codice. Cache dei tag per non riprocessare.

### Modulo 4 — Ideazione / generazione (`inkscout.ideation` + `inkscout.engine`)
- **Responsabilità:** da (reference selezionata **o** tema libero) + assi scelti → `Brief` strutturato → `DesignEngine.generate(brief)`.
- Cuore pluggable: vedi §5.

### Modulo 5 — Iterazione / refine (`inkscout.refine`)
- **Responsabilità:** varianti su un output ("più fine-line", "aggiungi il gufo", "gira in blackwork", "solo contorni"), regen con seed, editing del prompt/brief.
- **Storico versioni** del disegno (`design_version`), con diff del brief e lignaggio (parent_version_id).

### Modulo 6 — Export stencil (`inkscout.export`)
- **Responsabilità:** pipeline comune di post-processing su qualsiasi output raster.
- **Pipeline:** binarizzazione → pulizia linee → **upscale a 300 DPI** (non 72) → vettorializzazione.
- **Attenzione centerline:** `potrace`/inkscape producono **doppio-tratto** (contorno). Per tratto singolo usare **centerline** (`autotrace -centerline` / medial-axis). `vtracer` per output colore/veloce.
- **Output:** PNG 300 DPI **e** SVG. Watermark/label "AI-generated / reference only" sull'export.

### Modulo 7 — Web UI (`inkscout.web`)
- Server **stdlib** (`http.server`/`wsgiref`), coerente col pattern degli altri progetti. Nessun framework pesante.
- **Viste:** Brief builder · Moodboard · Galleria filtrabile (assi: stile/forma/colore/placement + **ricerca tema libera**) · Studio di generazione (selettore modo A–E) · Iterazione · Export.

---

## 5. Motore di generazione pluggable (il pezzo chiave)

Un solo contratto, N backend:

```python
class DesignEngine(Protocol):
    capabilities: EngineCapabilities  # needs_gpu, needs_key, cost_per_img, watermarks, offline
    def generate(self, brief: Brief) -> DesignResult: ...
    # DesignResult = moodboard | prompt | raster | svg (secondo il modo)
```

- **Modo E — `BriefEngine` (DEFAULT, no-API, offline).** Produce: **brief ricco** (stile + trattamento linea + soggetto + placement + size + line-weight) + **moodboard** (griglia di reference dalla libreria) + **prompt copia-incolla ottimizzato** (regola di prompting validata: *stile PRIMA* → "blackwork geometric" / "fine-line minimalist" + trattamento linea "bold black outlines" / "single-weight fine lines" + "tattoo stencil reference, white background, clear linework, no fuzzy edges" + negative prompt per togliere colore/sfondo/foto). Zero costi, zero GPU, zero rischio output. **Deliverable minimo, sempre disponibile.**
- **Modo A — `HostedAPIEngine` (opt-in, key in Keychain).** Provider astratto: **default fal.ai** (Flux Schnell ~$0.003/img, Flux+LoRA, Flux+ControlNet). Alternative dietro la stessa interfaccia: Replicate, Gemini/Nano-Banana (nota: **watermark SynthID**), Stability, ModelsLab. **Model-id e prezzi in config**, capability flags per UI.
- **Modo C — `Photo2StencilEngine` (opt-in).** ControlNet lineart/scribble (via fal.ai in cloud, o locale se GPU) per "trasforma questa foto/idea in linework" — è anche il veicolo della **vibe-di-X** (§6).
- **Modo B — `LocalDiffusionEngine` (opt-in, GPU, rimandato).** Flux/SDXL + LoRA tattoo (Civitai). Solo GPU NVIDIA ≥16GB; interfaccia predisposta, non implementata nell'MVP.
- **Modo D — `OpenCVEngine` (offline).** XDoG/Canny + vtracer/potrace. Non un "disegno", ma lo **step di export** (§6) condiviso da tutti i modi.

**Regola d'oro:** provider e modello dietro interfaccia, config-driven, con `EngineCapabilities`. Selettore di modo in UI che mostra costo/requisiti.

---

## 6. Pipeline "vibe di X" (stile via reference reali)

Obiettivo: ottenere il *feeling* di un artista raccolto **senza** spedire "in the style of [nome]".

1. Selezioni un artista/insieme di immagini dalla libreria (raccolto in §1).
2. `ideation` ne deriva **descrittori di stile neutri** (dai tag §3: es. "blackwork geometrico, tratto pieno, forte spazio negativo, simmetria") — **niente nome proprio** nel prompt.
3. Se il motore lo supporta (Modo A/C con ControlNet/IP-adapter), le **immagini reali** condizionano la generazione (image-conditioning) → resa più fedele del nome-nel-prompt.
4. Il brief conserva l'**attribuzione** all'artista come *reference*, con CTA "Commissiona questo artista" (§11), ma l'output è marcato AI/reference-only.

Vantaggio: più fedele, più difendibile, e non dipende dal fatto che una API accetti il nome.

---

## 7. Modello dati (SQLite, data-driven)

Tabelle principali (schema indicativo):

- `source` — `id, kind(upload|site|instagram|pinterest|tattoodo), ref, added_at, harvest_optin(bool), notes`
- `artist` — `id, name, handle, city, source_id, provenance_url, do_not_mimic(bool)`
- `image` — `id, path, phash, width, height, artist_id, source_id, source_url, license_note, fetched_at, favorite(bool), hidden(bool)`
- `style` — `id, name, aliases(json), parent_style_id, formal_attributes(json: palette/linework/density/typical_forms), description, is_emerging` — **popolata da `data/styles.seed.yaml`, estendibile**
- `image_style` — M2M `image_id ↔ style_id` (uno stesso pezzo può avere più stili)
- `image_tag` — `image_id, axis(subject|placement|color_mode|density|form), value(TEXT libero), confidence, tagger` — **subject/theme = TEXT libero + (opz.) embedding**
- `embedding` — `image_id/subject, vector(blob)` per il match semantico dei temi ("Twin Peaks")
- `design` — `id, title, brief(json), created_at`
- `design_version` — `id, design_id, parent_version_id, brief(json), engine, result_kind, asset_path, created_at`

**Vocabolari di assi** (form, size, placement, color_mode, density) = tabelle/seed lookup **separate e ortogonali**, combinabili liberamente. Nessuna di queste è un `enum` nel codice.

---

## 8. Flusso end-to-end (con l'esempio guida)

1. **Ingest.** Incolli l'handle IG di un tatuatore blackwork (harvest opt-in) o carichi immagini / dai l'URL del suo sito. → libreria + tagging.
2. **Sfogli.** Galleria filtrata per `form=round`, `color=black-only`; salvi preferiti.
3. **Ideazione.** Non trovi il pezzo giusto → apri lo Studio, imposti `forma=round` + `tema="Twin Peaks"` (testo libero). Il tema viene **espanso a runtime** in motivi visivi cercando nella libreria + embedding semantico (civetta, tende a zigzag, foresta di abeti, "Fire Walk With Me"…) — **nulla di ciò è scritto a mano**.
4. **Genera.** Modo E → brief + moodboard + prompt pronto. (Oppure Modo A con la key fal.ai → immagini reali; con vibe-di-X condizionata sul portfolio raccolto.)
5. **Itera.** "più minimale", "solo blackwork", "aggiungi la Log Lady" → nuove `design_version`.
6. **Export.** Stencil B/N, 300 DPI + SVG, label AI/reference-only → lo porti dal tatuatore.

---

## 9. Ingest & scraping — dettaglio operativo

- **HTTP-first** (`curl_cffi`) per ogni fonte; **CDP** (`nodriver`/Camoufox) solo su fallimento (JS-heavy/anti-bot).
- **Cache aggressiva** su disco (HTML/JSON/immagini) per non ripetere richieste e ridurre ban.
- **Harvest IG/Pinterest = modo personale opt-in**: banner esplicito "uso personale, viola i ToS, fragile", throttle + backoff lunghi, mai come servizio, mai ridistribuzione. `doc_id` IG **non hardcodati** (letti/aggiornabili).
- **Siti personali**: og:image, `<img>/srcset`, JSON-LD, `sitemap.xml` — via primaria e lecita.
- **Tool riusabili**: possibilità di delegare a `gallery-dl`/`instaloader` per l'harvest personale locale.

---

## 10. Tagging — dettaglio

- Default **CLIP zero-shot** locale su vocabolario `styles.seed.yaml`; **Vision LLM (Claude)** per sfumature/descrizioni libere.
- Output normalizzato sugli assi del §7. **Cache** dei risultati. **Validazione** su un campione (le fonti avvertono di allucinazioni su stile/posizione).

---

## 11. Guardie etiche / IP (nel prodotto, non opzionali)

1. **Framing**: moodboard/reference privato → *commissiona un tatuatore umano*. Non "tatuaggio finito da stampare".
2. **Niente "in the style of [artista vivente]"** nei prompt. Solo descrittori neutri + image-conditioning (§6).
3. **Niente scraping come feature-da-servizio**: harvest solo personale opt-in, con avvisi.
4. **Attribuzione** su ogni reference reale: credito + handle + link fonte + CTA "Commissiona questo artista". Mai rimuovere watermark/metadata.
5. **Labeling output**: ogni immagine AI marcata "AI-generated / reference only", con consiglio "il tatuatore ridisegni a mano".
6. **Opt-out artisti**: lista `do_not_ingest` / `do_not_mimic` (campo `artist.do_not_mimic`, filtro a monte).
7. **Provenance a DB** su ogni immagine; distinzione netta uso-personale/analisi vs redistribuzione (che **non** si fa).
8. **No training** su opere scrapate. Se in futuro LoRA, solo su opere licenziate/proprie o modelli "ethically trained".
9. **Disclaimer + nota giurisdizione**: reference informativo, non consulenza legale. Matteo è in **UE/Italia** → copyright + eccezioni più strette del fair use USA + **GDPR** (volti/handle possono essere dato personale). Da validare con legale IP prima di qualsiasi uso commerciale.

---

## 12. Stack tecnico

- **Python** moderno gestito con **uv**; lint/format **ruff**; test **pytest**. (Coerente con skill `modern-python`.)
- **Web**: stdlib (`http.server`/`wsgiref`) — niente framework pesante.
- **DB**: SQLite (WAL).
- **Scraping**: `curl_cffi` (HTTP-first), `nodriver`/Camoufox (CDP fallback), opz. `gallery-dl`/`instaloader` per harvest personale.
- **Immagini/export**: Pillow, `opencv-python`, `numpy`, `vtracer` (+ `potrace`/`autotrace` per centerline). **Tutti opzionali/lazy**: l'MVP modo E non li richiede.
- **Tagging**: CLIP (open_clip o transformers) opzionale; Vision LLM via API Claude opzionale.
- **Engine A**: client fal.ai (o `requests`); **API-key in macOS Keychain** (pattern come `omdb-key`/bzoom), es. voce `inkscout-fal-key`.
- **Config**: env prefix `INK_SCOUT_` (pattern come `TARIFFE_SCOUT_`), file config per provider/model-id/prezzi.
- **Dipendenze pesanti isolate** dietro `extras` (`pip install ink-scout[gen]`, `[tag]`, `[export]`) così il core resta leggero.

---

## 13. Scope MVP (v1) vs dopo (YAGNI)

**v1 (spedibile):**
- Ingest: `UploadAdapter` + `PersonalSiteAdapter` + `InstagramAdapter` (harvest personale opt-in).
- Libreria + dedup pHash + provenance.
- Tagging: `ClipTagger` (default) con vocabolario seed; `VisionLLMTagger` opzionale.
- Web UI: galleria filtrabile + preferiti + ricerca tema libera + moodboard.
- Ideazione: reference/tema → `Brief`.
- Engine: **Modo E** completo; **Modo A (fal.ai)** dietro key opt-in.
- Export: pipeline base 300 DPI + SVG (con nota centerline).
- Guardie §11 visibili in UI. Test.

**Dopo:**
- Modo B (locale GPU), Modo C avanzato (ControlNet/IP-adapter per vibe-di-X full).
- Pinterest/Tattoodo adapter.
- Refine avanzato (inpainting), storico versioni ricco.
- Embedding semantico dei temi su larga scala.

---

## 14. Rischi & mitigazioni

| Rischio | Mitigazione |
|---|---|
| ToS/ban IG/Pinterest (scraping vietato, ~200 req/h, doc_id ruotati) | Non è feature-da-servizio; harvest personale opt-in con throttle+backoff+cache; ingest primario upload/siti personali |
| Copyright output (riprodurre scelte espressive specifiche) | Framing reference-only, no "style of" nomi, label AI, consiglio redisegno a mano, no training su scrapato, dedup segnala copia 1:1 |
| Locale GPU fragile su Mac/MPS | GPU sempre opzionale; default cloud opt-in o OpenCV CPU; Modo B rimandato |
| Vendor lock-in / prezzi API volatili | Provider astratto; model-id/prezzi in config; capability flags |
| Qualità stencil (72 DPI, linee aperte, line-weight incoerente) | Pipeline export obbligatoria: binarizza → pulisci → 300 DPI → vettorializza |
| Doppio-tratto in vettorializzazione | Centerline (`autotrace -centerline`/medial-axis) per tratto singolo |
| Modello dati che invecchia | Style = tabella+gerarchia; Artist = seed+ingestion+provenance; Subject = testo libero+embedding |
| Reputazione community ("macchina per clonare") | Guardie §11 visibili: attribuzione, CTA commissione, opt-out, no imitazione mirata |
| Watermark SynthID (Google) | Dichiararlo in UI; per export "serio" preferire fal.ai/Flux o modo E/D |
| GDPR (UE/IT): volti/handle | Minimizzare dati personali, non legare a persone identificabili, provenance + base giuridica |

---

## 15. Domande aperte residue

- **Provider API secondario** dopo fal.ai (Gemini/Nano-Banana per qualità vs Stability/Replicate): si decide quando/se serve; l'interfaccia li supporta già.
- **Vocabolario stili iniziale**: quali stili nel primo `styles.seed.yaml` (dalla tassonomia della ricerca). Da rifinire in fase di piano.

Nessun blocco: si può procedere a `writing-plans`.
