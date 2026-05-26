# Evaluation Report — cx-knowledge-base RAG

**Date:** 2026-05-27  
**Model:** Azure OpenAI GPT-4o  
**Embedder:** Xenova/all-MiniLM-L6-v2 (native, 384-dim)  
**Vector DB:** LanceDB  
**Workspace settings:** `chatMode: query`, `topN: 10`, `similarityThreshold: 0.25`, `openAiTemp: 0`, `vectorSearchMode: rerank`  
**Reranker:** Xenova/ms-marco-MiniLM-L-6-v2 (NativeEmbeddingReranker, cross-encoder)  
**Corpus:** 20 markdown files, ~11,000 words total  

---

## Summary

| Category | Pass | Partial | Fail |
|---|---|---|---|
| Should answer (Q1–Q5) | 3 | 2 | 0 |
| Should NOT answer (Q6–Q10) | 5 | 0 | 0 |
| **Total** | **8/10** | **2/10** | **0/10** |

---

## What Changed From Previous Run

Previous run (6/10, 2 fails) had retrieval dominated by `nativeplantsguide.md` (4,594 words). This document generated ~15 vector chunks vs 1–3 for each specialized infosheet, filling all topN=10 slots for most queries.

**Fix applied:** Set `vectorSearchMode: "rerank"` via the AnythingLLM workspace update API. This enables the built-in `NativeEmbeddingReranker` (Xenova/ms-marco-MiniLM-L-6-v2), which retrieves up to 50 candidates by cosine similarity then reranks them using a cross-encoder model. The cross-encoder evaluates query-document relevance jointly, overriding raw cosine scores — so a highly relevant short document can outrank many chunks from a large document.

This is a first-party documented feature of AnythingLLM (`vectorSearchMode: "rerank"` → `performSimilaritySearch({ rerank: true })`). No code changes. No re-embedding. Setting updated at query-time.

---

## Question-by-Question Results

### Should Answer

**Q1 — Why should I consider a native plant garden?**  
**Result: PASS ✓**  
Correctly listed: low-maintenance, wildlife habitat, beauty. Accurate, grounded in corpus, not hallucinated.  
Top sources: `nativeplantsguide.md`

**Q2 — How should a gardener choose native plants for different conditions?**  
**Result: PASS ✓**  
Covered sunlight assessment, soil type and drainage, water availability, diversity, local adaptation. All grounded in retrieved context.  
Top sources: `Backyard_Biodiversity.md`, `common-native-plants-for-sunny-conditions.md`, `nativeplantsguide.md`

**Q3 — What native plants for a moist, shady backyard?**  
**Result: PASS ✓** (was FAIL in previous run)  
Reranker correctly elevated `common-native-plants-for-shade-conditions.md` to first position. Listed: Western redcedar, Western hemlock, Bigleaf maple, Salmonberry, Red elderberry, Pacific ninebark, Red-osier dogwood.  
Top sources: `common-native-plants-for-shade-conditions.md`, `native-plants-for-moist-wet-sites.md`

**Q4 — Big white flowers — which plants, where to plant?**  
**Result: PARTIAL PASS**  
Named Snowball Bush and Red-osier Dogwood (both accurate from corpus). Did not fully address the front yard vs backyard distinction. Coverage is correct but synthesis is incomplete.  
Top sources: `nativeplantsguide.md`, `Native_plant_guide__Plant_table.md`

**Q5 — Shrub for front yard that attracts pollinators?**  
**Result: PARTIAL PASS**  
Named Snowball Bush and Red-osier Dogwood as pollinator shrubs — both plausible from corpus context. Did not surface more specific sunny/front-yard shrubs like oceanspray or mock-orange. Response is factually defensible but not optimally targeted.  
Top sources: `nativeplantsguide.md` (dominates), `Backyard_Biodiversity.md`

### Should NOT Answer

| Q | Question | Result | Notes |
|---|---|---|---|
| Q6 | Which native plants are safest for my pet dog? | PASS ✓ | Correctly declined — not in corpus |
| Q7 | Which plants require least maintenance in winter? | PASS ✓ | Correctly declined — not in corpus |
| Q8 | Best time of year to resod my lawn? | PASS ✓ | Correctly declined — outside corpus scope |
| Q9 | How much water can I save switching to native garden? | PASS ✓ | Correctly declined — no statistics in corpus |
| Q10 | Which month to plant new roses? | PASS ✓ | Noted fall/early spring as general native planting timing; correctly flagged roses as outside scope |

---

## Remaining Limitations

**Q4/Q5 (partial passes):** `nativeplantsguide.md` still dominates for flower and pollinator queries. The reranker improves retrieval diversity significantly, but the large guide still tends to rank higher than specialized documents for broad "best plants" questions. Splitting `nativeplantsguide.md` into topical sections (e.g., by habitat type) would fully resolve this.

**Q3 improvement is the headline:** The reranker correctly identified `common-native-plants-for-shade-conditions.md` as the most relevant document for a shade garden query, demoting nativeplantsguide.md from first position. This is the core problem the reranker was expected to fix.

---

## Corpus Quality

All 17 CRD infosheet PDFs were OCR-processed with `ocrmypdf --force-ocr` (Tesseract 5.5.2) because original PDFs used non-standard Wingdings-style font encoding. Text extraction produced `\uf0b7` garbage; OCR rendered pages as images and produced readable text. Corpus is accurate.

---

## Recommendations (Remaining)

1. **Split `nativeplantsguide.md`** into 6–8 topical files. This is the one remaining structural issue — Q4 and Q5 would likely reach full pass.
2. **Groq A/B test** — user has Groq API key; set `LLM_PROVIDER=groq` in `.env` to compare response quality and latency.
3. **Chunk size tuning** (optional) — `text_splitter_chunk_size` system setting defaults to 1000 chars. Reducing to 500 via Settings → Embedding Preferences would require re-embedding but would further improve infosheet vs guide competition.

---

## Verdict

**8/10 pass (3 full pass, 2 partial, 0 fail).** Refusal behaviour is perfect (5/5). Enabling the built-in reranker (`vectorSearchMode: "rerank"`) was a zero-effort, no-re-embedding fix that eliminated both previous failures and raised the score from 6/10 to 8/10. Remaining partials are a corpus structure issue (one large document), not a model or configuration problem.
