# CX Knowledge Base

A local AI assistant pre-loaded with native plants documentation for British Columbia. Ask it questions and it answers only from the embedded documents — no hallucinations, no internet, no general knowledge drift.

---

## Quick Start (non-technical)

**What you need before starting:**
- Docker Desktop installed and running
- Your Azure OpenAI API key (ask your team lead)
- Git

**Steps:**

1. **Download the project**
   Open Terminal and run:
   ```
   git clone https://github.com/cds-snc/cx_anythingllm_knowledgebase.git
   cd cx_anythingllm_knowledgebase
   ```

2. **Create your config file**
   ```
   cp .env.example .env
   ```
   Open `.env` in any text editor. Fill in these three lines with your credentials:
   ```
   AZURE_OPENAI_KEY=your-key-here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   ```
   Save and close the file.

3. **Install the knowledge base**
   ```
   bash scripts/install.sh
   ```
   This downloads the app, loads the pre-embedded document library, and starts everything. Takes about 2–3 minutes the first time.

4. **Open the assistant**
   Go to [http://localhost:3001](http://localhost:3001) in your browser.
   - Create an account when prompted (this is local to your machine)
   - Select the **CX Knowledge Base** workspace
   - Type your question and press Enter

5. **Stop the assistant when done**
   ```
   docker-compose down
   ```
   Your data is saved — next time just run `docker-compose up -d` to restart.

**To get the latest document updates:**
```
bash scripts/update.sh
```

---

## What's happening under the hood

The assistant is [AnythingLLM](https://anythingllm.com) running locally in Docker. When you ask a question:

1. Your question is converted to a vector (a numerical fingerprint) by a small model running inside the container — no API call, no cost.
2. That vector is compared against the pre-embedded document library using LanceDB, a file-based vector database stored in `./storage/`.
3. The most relevant passages from the documents are retrieved and sent, along with your question, to **Azure OpenAI gpt-4o** (your org's CDS endpoint).
4. gpt-4o synthesises an answer using only those passages. The workspace is in **Query mode**, which means it will say "I don't know" rather than guess if the answer isn't in the documents.

Everything except the final LLM call runs locally. The document vectors never leave your machine.

---

## Technical reference

### Stack

| Component | Technology |
|-----------|------------|
| App | AnythingLLM v1.12+ (Docker) |
| LLM | Azure OpenAI gpt-4o (CDS org endpoint) |
| Embedder | Xenova/all-MiniLM-L6-v2 (native, in-container) |
| Vector DB | LanceDB (file-based, `./storage/lancedb/`) |
| Transcription | Whisper (local) |
| Database | SQLite (`./storage/anythingllm.db`) |

### Corpus

21 documents in `documents/`:
- 19 PDFs: native plant guides (shade, sun, seashore, rock garden, meadow, butterfly, wildlife, edible plants, etc.)
- 1 DOCX: Backyard Biodiversity guide
- 2 XLSX: Museum of Vancouver Indigenous plant guide, plant reference tables

All documents are embedded with 384-dimension vectors (all-MiniLM-L6-v2).

### Environment variables

See `.env.example`. Critical vars:

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Base URL, e.g. `https://cds-platform-ai.openai.azure.com/` |
| `AZURE_OPENAI_MODEL_PREF` | Deployment name, default `gpt-4o` |
| `EMBEDDING_ENGINE` | Set to `native` (free, in-container) |
| `VECTOR_DB` | Set to `lancedb` |
| `ANYWHERE_API_KEY` | AnythingLLM API key (auto-generated on first run) |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install.sh` | Fresh install: pulls image, loads corpus snapshot, starts container |
| `scripts/update.sh` | Pull latest corpus snapshot from GitHub Releases and restart |
| `scripts/pack-storage.sh <tag>` | Package current `storage/` as a release tarball |
| `scripts/test.sh` | End-to-end test suite (14 checks) |

### Running tests

```bash
bash scripts/test.sh
```

All 14 checks must pass before releasing. Tests cover: container health, API auth, workspace state, Azure LLM config, 3 live query validations, and anti-hallucination mode.

### Releasing a new corpus version

```bash
# 1. Add documents to documents/, embed them in the UI
# 2. Package and publish
bash scripts/pack-storage.sh v$(date +%Y-%m-%d)
# Run the gh release create command it outputs
```

### API access

The AnythingLLM REST API is available at `http://localhost:3001/api/v1/`. Authenticate with the `ANYWHERE_API_KEY` from your `.env`:

```bash
curl -X POST http://localhost:3001/api/v1/workspace/cx-knowledge-base/chat \
  -H "Authorization: Bearer $ANYWHERE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"What native plants grow well in shade?","mode":"query"}'
```
