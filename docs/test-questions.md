# Evaluation Questions — CX Knowledge Base

## Evaluator context

The following questions are asked in the context of this user scenario:

> *"I have just moved house, and I want to redo my garden. I live on Vancouver Island, where my front yard gets good direct sun, and my backyard is fairly shaded."*

---

## Questions the model SHOULD answer

These test whether the model retrieves and synthesises information correctly from the corpus.

---

### Q1 — Semantic synthesis

**Question:** Why should I consider a native plant garden?

**Expected behaviour:** Discuss benefits such as biodiversity enhancement, wildlife support, erosion control, low-maintenance, etc.

---

### Q2 — Semantic synthesis

**Question:** How should a gardener choose native plants for different conditions in their yard?

**Expected behaviour:** Discuss choosing plants based on sunlight, moisture, wildlife goals, and/or seasonal or aesthetic interest.

---

### Q3 — Direct retrieval

**Question:** What native plants are recommended for my moist, shady backyard garden?

**Expected behaviour:** Provide plant examples such as salal, sword fern, willow, Pacific bleeding heart, etc.

---

### Q4 — Multi-constraint reasoning

**Question:** I like the look of big white flowers in my garden. Which plants would achieve this? Where could I plant them?

**Expected behaviour:** Provide plant examples for the front yard (e.g., Sitka mountain ash, red elderberry, mock-orange), backyard (e.g., fringecup, lily-of-the-valley), or either (e.g., dogwood, thimbleberry, ninebark).

---

### Q5 — Cross-document retrieval

**Question:** I need a new shrub in my front yard that would also attract pollinators. What are some options?

**Expected behaviour:** Provide plant examples such as snowberry, oceanspray, currant, mock-orange, cinquefoil, rose, etc.

---

## Questions the model SHOULD NOT answer

These test whether the model correctly declines to answer when the corpus does not contain sufficient information. A correct response acknowledges the gap — it does not hallucinate.

---

### Q6 — Missing attribute

**Question:** Which native plants are safest if I have a pet dog?

**Expected behaviour:** Acknowledge that pet safety specifically is not covered in the documents. The model should not produce a safety-ranked plant list.

---

### Q7 — Missing attribute

**Question:** Which native plants require the least maintenance during winter?

**Expected behaviour:** Acknowledge that the documents do not define or rank plants by winter maintenance. Any guidance given should rely only on proxy attributes from the documents (e.g., habitat suitability, evergreen characteristics) — not a fabricated ranking.

---

### Q8 — Domain-boundary hallucination

**Question:** What is the best time of year to resod my lawn?

**Expected behaviour:** Note that the documents focus on native and natural gardening, which encourages moving away from a manicured lawn, and that lawn reseeding is outside their scope.

---

### Q9 — Numerical hallucination

**Question:** How much water can I expect to save in a year by switching to a native garden instead of a traditional lawn?

**Expected behaviour:** Acknowledge that native gardens generally reduce water use, but decline to provide percentage or numerical claims that are not in the documents.

---

### Q10 — Temporal hallucination

**Question:** Which month should I plan to plant new roses in my garden?

**Expected behaviour:** Note that the best time to plant native plants is generally fall or early spring, but avoid over-precise timing claims that may be conflated with bloom periods from the plant table.
