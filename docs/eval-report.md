# Evaluation Report — CX Knowledge Base

**Date:** 2026-05-26  
**Configuration:** `chatMode=query`, `temperature=0`, `similarityThreshold=0.45`, `topN=6`  
**Corpus:** 21 documents (BC native plant guides)

---

## Summary

| # | Question type | Verdict |
|---|---|---|
| Q1 | Semantic synthesis — why native plants? | ✅ Pass |
| Q2 | Semantic synthesis — choosing plants for conditions | ✅ Pass |
| Q3 | Direct retrieval — moist shady backyard | ⚠️ Partial |
| Q4 | Multi-constraint — big white flowers | ❌ Fail (hallucination) |
| Q5 | Cross-document — pollinator shrubs, sunny front yard | ⚠️ Partial |
| Q6 | Missing attribute — pet dog safety | ✅ Pass |
| Q7 | Missing attribute — winter maintenance | ✅ Pass |
| Q8 | Domain-boundary — resodding a lawn | ✅ Pass |
| Q9 | Numerical hallucination — water savings | ✅ Pass |
| Q10 | Temporal hallucination — when to plant roses | ⚠️ Borderline |

**Score: 6/10 clean passes. 2 partial retrievals, 1 hallucination, 1 borderline.**

---

## Detailed results

---

### Q1 — Why should I consider a native plant garden?

**Verdict: ✅ Pass**  
**Sources cited: 6**

> Considering a native plant garden offers several benefits... Low Watering Needs, Support for Biodiversity, Low Maintenance, Rainwater Management, Soil Health, Sustainability.

Well-synthesised. All claims are grounded in the type of content found in native plant guides. Doesn't over-reach. Lists six distinct benefits with brief explanations. Consistent with expected answer.

---

### Q2 — How should a gardener choose native plants for different conditions?

**Verdict: ✅ Pass**  
**Sources cited: 6**

> Assess your property's conditions... Set gardening goals... Select plants based on conditions.

Covers sunlight, shade, water, soil, wildlife goals, and seasonal interest — all expected dimensions. Well-structured, actionable advice grounded in the corpus.

---

### Q3 — Native plants for a moist, shady backyard?

**Verdict: ⚠️ Partial**  
**Sources cited: 6**

> Western Redcedar, Western Hemlock, Sword Fern, Deer Fern, False Lily-of-the-valley.

**What it got right:** Sword fern is a classic expected answer. Ferns generally are correct. All plants listed are plausibly in the corpus.

**What it missed:** Key expected examples — salal, Pacific bleeding heart, willow — were not retrieved, despite being common in BC shade gardening guides. Western Redcedar and Western Hemlock are large trees, not practical for a residential backyard; recommending them as garden plants without qualification is misleading.

**Root cause:** `topN=6` may not be retrieving the most relevant chunks. The query matched tree-focused documents before shrub/ground-cover guides.

---

### Q4 — Big white flowers — which plants and where?

**Verdict: ❌ Fail (hallucination)**  
**Sources cited: 2 (lowest of all questions)**

> Pacific Rhododendron (Rhododendron macrophyllum) — "large, showy white flowers"  
> Wood sorrel (Oxalis oregana) — white to pink flowers  
> Fringecup — white flower spires (backyard)

**Critical issue:** *Rhododendron macrophyllum* (Pacific rhododendron) is not known for white flowers — it produces pink to deep rose-purple blooms. The model described it as having "large, showy white flowers," which is factually incorrect and not supported by the documents. This is a hallucination.

**Wood sorrel** (*Oxalis oregana*) produces small flowers, not "big white flowers." Describing it as meeting that criterion is misleading.

**What it missed:** The expected examples — mock-orange, dogwood, thimbleberry, ninebark, red elderberry — were not retrieved at all. The low source count (2) indicates the similarity search did not find the most relevant material for this multi-constraint query.

**Action required:** This is the most significant failure. The model fabricated a flower colour for a well-known plant. Even at temperature=0, the model apparently inferred/hallucinated a plant description rather than citing the documents directly.

---

### Q5 — Pollinator shrubs for a sunny front yard?

**Verdict: ⚠️ Partial**  
**Sources cited: 6**

> Red-osier dogwood, Thimbleberry, Pacific ninebark.

**What it got right:** Pacific ninebark and thimbleberry are legitimate pollinator-attracting native shrubs with white flowers. Ninebark is well-suited to the corpus.

**What it missed:** Snowberry, oceanspray, currant, mock-orange, and cinquefoil — the expected core examples — were not retrieved. Red-osier dogwood is primarily a moisture-tolerant shrub and a questionable recommendation for a "good direct sun" front yard without that qualification.

**Assessment:** The model retrieved real plants from the corpus but not the most on-point ones. The answer is partially correct but incomplete for a sunny-front-yard context.

---

### Q6 — Which plants are safe for a pet dog?

**Verdict: ✅ Pass**  
**Sources cited: 6**

> The provided documents do not contain specific information about the safety of native plants for pets, including dogs... For information on pet-safe plants, you may need to consult additional resources or contact a local gardening expert or veterinarian.

Clean refusal. Correctly identifies that pet safety is not in the corpus. Does not fabricate a list. Refers user to appropriate external resources. This is exactly the expected behaviour.

---

### Q7 — Which plants require least winter maintenance?

**Verdict: ✅ Pass**  
**Sources cited: 6**

> The documents provided do not specifically address which native plants require the least maintenance during winter. They do mention that evergreen trees are particularly important in the winter months... However, for specific information on low-maintenance native plants during winter, additional resources or expert advice may be needed.

Well-handled. Accurately says the gap exists. Uses evergreen characteristics as a proxy attribute from the documents — which is exactly what the expected behaviour called for. Does not produce a fabricated ranking.

---

### Q8 — Best time to resod a lawn?

**Verdict: ✅ Pass**  
**Sources cited: 0**

> The documents provided do not contain specific information about the best time of year to resod a lawn... They focus on native plant gardening.

Zero sources cited — the similarity search found nothing relevant (correct, since the corpus doesn't cover lawn reseeding). The model correctly stays silent rather than inventing lawn-care advice.

**Note:** The expected behaviour also included noting that the corpus *encourages moving away from lawns entirely*. The model didn't make that connection, but it didn't hallucinate either. Minor missed opportunity.

---

### Q9 — How much water will I save by switching to a native garden?

**Verdict: ✅ Pass**  
**Sources cited: 4**

> The documents provided do not contain specific information on the amount of water you can expect to save... They do mention that native plants are adapted to local conditions and generally require less water... However, exact figures or estimates for water savings are not provided.

Correct. Acknowledges the general principle (less water needed) without inventing percentages or statistics. This is the expected behaviour.

---

### Q10 — Which month should I plant roses?

**Verdict: ⚠️ Borderline**  
**Sources cited: 0**

> The documents provided do not specifically mention roses... they do suggest that native plants should be planted in the fall... While this advice is specific to native plants, it might be beneficial to consider similar timing for other types of plants, such as roses.

**Issue:** The final sentence — "it might be beneficial to consider similar timing for... roses" — extrapolates from native plant planting guidance to non-native roses. This is mild general-knowledge inference that goes beyond the documents. The model should have stopped after noting that roses are outside the scope of the corpus.

Zero sources were cited, which correctly reflects that no relevant document was found — yet the model still offered a suggestive recommendation. This is a soft failure of the strict-only-from-documents requirement.

---

## Configuration issues found

### 1. ANYWHERE_API_KEY not written to `.env`

The `.env` file still contains the placeholder value `your-anythingllm-api-key-here`. The API key must be retrieved manually from the container's SQLite database on each fresh install. This key needs to be written to `.env` at the end of `install.sh` (after the container starts and generates the key).

### 2. Similarity threshold may be too high for multi-constraint queries

Q4 retrieved only 2 sources — the lowest of any question. The 0.45 threshold is filtering out relevant chunks for complex, multi-attribute queries. Consider lowering to 0.35 for better recall, accepting that precision may drop slightly on edge cases.

### 3. System prompt does not prevent description fabrication

Q4 demonstrates that the model will invent plant descriptions (flower colour) even at temperature=0 when it finds a plant name in the corpus but not the specific attribute being asked about. The system prompt needs an explicit instruction: **"If a document mentions a plant but does not confirm the specific attribute being asked about, do not describe that attribute."**

---

## Recommended fixes

| Priority | Fix |
|----------|-----|
| **High** | Add post-start step to `install.sh` that writes the real `ANYWHERE_API_KEY` to `.env` |
| **High** | Update system prompt to prohibit describing plant attributes not explicitly stated in source documents |
| **Medium** | Lower `similarityThreshold` from 0.45 → 0.35 and retest Q3, Q4, Q5 |
| **Medium** | Add Q4 and Q5 as regression checks to `test.sh` (currently tests only 3 queries) |
| **Low** | Rewrite Q8 refusal to note that the corpus actively discourages lawn-focused gardening |
