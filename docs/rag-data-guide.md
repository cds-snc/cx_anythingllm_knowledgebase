# RAG Data Quality Guide
**For researchers managing knowledge base content**

---

## How retrieval actually works

When a user asks a question, the system doesn't read your documents. It converts the question into a vector (a list of numbers representing meaning) and finds the text chunks in the database that are mathematically closest to it. The LLM only sees those chunks — nothing else.

This means **what the LLM can answer is entirely determined by what gets retrieved**, and what gets retrieved is determined by how well your document chunks match the user's query. Quality of answer = quality of data going in.

---

## The core rule: one topic per document

The retrieval system has no concept of "this is a long document covering many things." It sees chunks of ~150 words each and scores them individually. If you upload a 50-page product manual as one file, its chunks are competing with each other for retrieval slots.

**One document = one topic.** Not one product, not one meeting, not one quarter.

---

## What good data looks like

### ✅ Support documentation

```markdown
# Login error: "Invalid credentials" on SSO

**Applies to:** Enterprise plan, SAML SSO setup  
**Product area:** Authentication

## What the user sees
Error message: "Invalid credentials" when logging in via SSO even with correct password.

## Cause
Session token expires after 8 hours. SSO redirect does not trigger re-authentication.

## Resolution
1. Clear browser cookies for the app domain.
2. Have the user log out completely and log back in.
3. If issue persists, check the SAML assertion expiry in your IdP config.

## Escalation path
If clearing cookies does not resolve: raise with backend-auth team, reference ticket tag AUTH-SSO.
```

**Why it works:** One issue. Specific title that matches how a user would describe the problem. Clear structure. Findable by "SSO", "login error", "invalid credentials", "session token."

---

### ✅ Feature request (captured cleanly)

```markdown
# Feature request: bulk export for customer reports

**Source:** Customer call with Acme Corp, 2026-04-12  
**Requested by:** Operations team  
**Priority signal:** Blocking their monthly reporting workflow

## Request summary
Customer wants to export all customer report data as CSV in a single operation. 
Currently exporting one report at a time. At 200+ reports, this takes 2-3 hours monthly.

## Exact quote
"We spend half a day every month clicking export. If we could just do it all at once, 
that would eliminate the whole problem."

## Relevant context
They currently use the Reports > Export > CSV path. No current bulk option exists.
Related existing ticket: FR-2201 (dashboard export).
```

**Why it works:** One request per document. Structured extraction, not raw transcript. The key information is surfaced at the top where it lands in the first chunks the retriever sees.

---

### ❌ Meeting notes (raw dump) — avoid this

```
April 12 sync with Acme Corp

Attendees: Sarah, Marcus, Tim (us), Janet (them)

We started by talking about their Q2 roadmap and then Sarah mentioned the 
holiday schedule. Tim asked about the pricing change. Janet said the team 
had concerns about the new dashboard layout, particularly the filter panel, 
but wasn't sure if it was a training issue or a UX issue. Marcus mentioned 
we'd look into it. There was also a mention of the bulk export thing again — 
apparently it's still a problem for them. We said we'd put it in the backlog. 
Sarah made a joke about the weather. The call ended a bit early.
```

**Why it fails:** Raw transcript noise fills the chunks. "Holiday schedule", "pricing change", "Sarah made a joke" all appear in the same chunks as the actual signal. A question about bulk export retrieves chunks full of irrelevant conversation. The LLM either hallucinates or misses the answer entirely.

**Fix:** Extract before you upload. Pull out the feature request, the UX concern, and the action items as separate documents. Discard the rest.

---

### ❌ The omnibus document problem

`nativeplantsguide.md` is a real example from this project. It's a 4,600-word guide covering plant selection, soil prep, watering, mulching, sourcing, and seasonal care — all in one file. It generates ~30 chunks. A 400-word infosheet on shade plants generates 3 chunks.

For a query like "what plants for a shaded backyard," cosine similarity alone fills all retrieval slots with chunks from the big guide — even after the reranker, broad questions still prefer it. The specialized infosheet that directly answers the question gets crowded out.

**Equivalent in your context:** Uploading a full product spec or a year-end roadmap document. Every question about any feature pulls from it. Specific documents about individual features never surface.

---

## Document prep checklist

Before uploading any document:

- [ ] **One topic?** If you can summarize it in one sentence, it's probably fine. If it takes three, split it.
- [ ] **Descriptive title?** The filename becomes metadata on every chunk. `login-sso-error.md` retrieves better than `support-issues-batch-3.md`.
- [ ] **Key info at the top?** The first 150 words of a document land in the first chunk, which tends to score highest. Put the most searchable content there.
- [ ] **Noise removed?** For meeting notes, customer calls, Slack threads: extract the signal before uploading. Raw transcripts are almost always wrong to upload as-is.
- [ ] **Right scope?** A feature request and a bug report about the same feature should be separate documents, not merged.

---

## Data types and how to handle them

| Type | Best approach |
|---|---|
| Support docs / FAQs | Upload as-is if one topic per doc. Split if multi-topic. |
| Product specs | Split by feature area. Never upload the full spec. |
| Meeting notes / call recordings | Extract: decisions, action items, feature requests, pain points. Upload the extraction, not the raw notes. |
| Feature requests | One doc per request. Include: what was asked, who asked, why, exact quote if available. |
| Slack threads / email chains | Too noisy to upload raw. Summarize the outcome and the key ask into a structured doc. |
| PDFs with columns / scanned pages | Check the extracted text before uploading — OCR artifacts break retrieval silently. |

---

## The test: would a human make sense of this chunk out of context?

Pinecone's guidance puts it simply: *"If the chunk of text makes sense without the surrounding context to a human, it will make sense to the language model."*

If you cut a random 150-word section out of your document and it reads like a coherent standalone thought — good. If it reads like half a sentence and references "the issue mentioned above" — that chunk will retrieve poorly and potentially mislead the LLM.

---

## Sources

- Pinecone: *Chunking Strategies for LLM Applications* (2025)
- Microsoft Azure: *RAG Preparation Phase* and *RAG Chunking Phase* — Azure Architecture Center
- Anthropic: *Introducing Contextual Retrieval* (2024)
