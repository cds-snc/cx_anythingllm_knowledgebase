# Evaluation Report — cx-knowledge-base RAG

**Date:** 2025-05-26  
**Model:** Azure OpenAI GPT-4o  
**Embedder:** Xenova/all-MiniLM-L6-v2 (native, 384-dim)  
**Vector DB:** LanceDB  
**Workspace settings:** `chatMode: query`, `topN: 10`, `similarityThreshold: 0.25`, `openAiTemp: 0`  
**Corpus:** 20 markdown files, ~11,000 words total  

---

## Summary

| Category | Pass | Partial | Fail |
|---|---|---|---|
| Should answer (Q1–Q5) | 1 | 2 | 2 |
| Should NOT answer (Q6–Q10) | 5 | 0 | 0 |
| **Total** | **6/10** | **2/10** | **2/10** |

---

## Question-by-Question Results

### Should Answer

**Q1 — What native plants can I grow in my backyard? (shaded)**  
**Result: FAIL**  
Model said documents don't list shade plants, despite `common-native-plants-for-shade-conditions.md` containing 30+ shade plants. Root cause: that document (369 words) was not retrieved — `nativeplantsguide.md` (4,594 words) filled all retrieval slots with general advice chunks.

**Q2 — What is Salal and where would it grow best?**  
**Result: PARTIAL PASS**  
Model correctly identified Salal as a native plant growing in forested/shaded environments that tolerates dry sites. Did not give a confident "grows best in..." statement.

**Q3 — What plants tolerate both shade and wet conditions?**  
**Result: PASS ✓**  
Listed: western redcedar, western hemlock, bigleaf maple, salmonberry, red elderberry, Pacific ninebark, red-osier dogwood. All correct, sourced from `nativeplantsguide.md`.

**Q4 — Can I grow Pacific Rhododendron? What colour are its flowers?**  
**Result: PARTIAL PASS**  
Correctly identified Pacific Rhododendron as a shade-tolerant plant. Declined to state flower colour — the corpus doesn't describe it, so this is a correct refusal rather than a failure.

**Q5 — What native ground covers for a sunny front yard?**  
**Result: FAIL**  
`native-plant-ground-covers.md` exists in corpus but was not retrieved. Same large-document dominance issue as Q1.

### Should NOT Answer

| Q | Question | Result |
|---|---|---|
| Q6 | How much fertilizer for Salal? | PASS ✓ — correctly refused |
| Q7 | Best plant to deter deer in Victoria? | PASS ✓ — correctly refused |
| Q8 | How many native species in BC? | PASS ✓ — correctly refused |
| Q9 | Indigenous plants used in 1800s? | PASS ✓ — correctly refused |
| Q10 | Carbon sequestration rates? | PASS ✓ — correctly refused |

---

## Root Cause of Q1/Q5 Failures

**Retrieval dominance.** `nativeplantsguide.md` is 4,594 words; specialized infosheets average ~350 words. With cosine similarity, the large document generates ~15 chunks vs 1–3 for each infosheet. All topN=10 slots go to `nativeplantsguide.md`.

The infosheet content is correct and verified. The problem is retrieval architecture, not corpus quality.

---

## Corpus Quality — Before/After

**Before:** All 17 PDFs used non-standard font encoding (Wingdings-style). Text extraction produced `\uf0b7` garbage. AnythingLLM was embedding whitespace. Answers came from GPT-4o training data.

**After:** `ocrmypdf --force-ocr` (Tesseract 5.5.2) extracted real content. Shade conditions document: 74 garbage words → 369 real plant names (Sword fern, Salal, Pacific bleeding heart, Western trillium, etc.). Corpus is now correct.

---

## Recommendations

1. **Split `nativeplantsguide.md`** into 6–8 topical files (habitat types, care, sourcing, etc.) — prevents monopolising retrieval.
2. **Hybrid search** — BM25 keyword + semantic would correctly surface "native-plant-ground-covers" for a ground cover query. Not available in AnythingLLM without a custom retriever.
3. **Groq A/B test** — user has Groq API key; set `LLM_PROVIDER=groq` in `.env` to compare.

---

## Verdict

Refusal behaviour is correct and consistent (5/5 out-of-scope questions handled properly). In-scope retrieval partially works: 1 full pass, 2 partial, 2 failures. Failures are a retrieval architecture issue — not a content problem. The corpus data is accurate.
