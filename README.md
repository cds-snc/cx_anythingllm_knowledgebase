# CX AnythingLLM Knowledge Base

RAG-based research corpus using [AnythingLLM](https://anythingllm.com/), running locally in Docker. Zero network exposure. Corpus syncs via GitHub Releases.

## Stack

| Layer | Choice | Why |
|---|---|---|
| LLM | OpenAI `gpt-4o-mini` | Cost-effective, reliable for RAG |
| Embedder | OpenAI `text-embedding-3-small` | High quality, affordable |
| Vector DB | LanceDB (built-in) | Zero external dependency, portable |
| Chat Mode | **Query** (document-only) | Prevents hallucination |

See [docs/distribution-strategy.md](docs/distribution-strategy.md) for the full team-distribution plan.

---

## Teammate Install (3 steps)

**Prerequisites:** Docker Desktop or Colima, an OpenAI API key.

```bash
git clone https://github.com/cds-snc/cx_anythingllm_knowledgebase.git
cd cx_anythingllm_knowledgebase
./scripts/install.sh
```

The install script:
1. Checks Docker is running
2. Creates `.env` from `.env.example` (prompts for your OpenAI key)
3. Downloads the latest embedded corpus from GitHub Releases
4. Starts AnythingLLM at **http://localhost:3001**

**On macOS with Colima** (instead of Docker Desktop), start Colima first:
```bash
colima start --arch aarch64 --memory 4 --cpu 2
export DOCKER_HOST="unix://$HOME/.colima/docker.sock"
```

---

## Update to Latest Corpus

```bash
./scripts/update.sh
```

Downloads the latest storage snapshot from GitHub Releases and restarts the container. Safe to run at any time — backs up your current storage first.

---

## Start / Stop

```bash
docker-compose up -d      # start
docker-compose down       # stop
docker-compose logs -f    # view logs
```

---

Open: **http://localhost:3001**

---

## First-Time Setup (run once after first start)

1. Open http://localhost:3001 and complete the onboarding wizard.
2. The wizard will pre-populate from `.env` — verify LLM shows **OpenAI / gpt-4o-mini** and Embedder shows **OpenAI / text-embedding-3-small**.

### Create the research workspace

After onboarding:

1. Click **New Workspace** → name it `Research`.
2. Open workspace **Settings** (gear icon) → **Chat Settings** tab.
3. Set **Chat Mode → Query** — this is the anti-hallucination setting. The model will only answer from embedded documents and will say so if it can't find relevant content.
4. Set this system prompt (paste into System Prompt field):

```
You are a research assistant. Answer ONLY using information found in the provided documents. 
If the answer is not in the documents, say: "I could not find that information in the provided documents."
Do not speculate, infer, or use outside knowledge. Cite the document section when possible.
```

5. In **Vector Database Settings**, set **Document Similarity Threshold** to `Medium (≥ 0.50)` to start. Drop to `No restriction` if you're getting too many "no relevant info" responses.

---

## Uploading Documents

Drop files via the UI:

1. Click the **Upload** button (paper-clip icon in sidebar).
2. Upload one or more files (PDF, DOCX, TXT, MD, etc.).
3. Select the uploaded files and click **Move to Workspace → Research**.
4. Files are now embedded and searchable.

Supported formats: PDF, DOCX, TXT, MD, CSV, JSON, HTML, XML, EPUB, and more.

---

## Test Document

A sample test document is in `documents/test-corpus.txt`. Upload it first to confirm the pipeline works end-to-end before loading the full corpus.

---

## Adding More Documents (bulk)

Stage files in the `documents/` folder locally, then upload via the UI drag-and-drop. The folder is committed (without secrets) as a staging area.

---

## Configuration

All runtime config is in `.env` (gitignored). To change LLM or embedder:

1. Edit `.env`
2. `docker compose restart anythingllm`

Key environment variables:

| Variable | Current Value | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM backend |
| `OPEN_MODEL_PREF` | `gpt-4o-mini` | Model |
| `EMBEDDING_ENGINE` | `openai` | Embedder backend |
| `EMBEDDING_MODEL_PREF` | `text-embedding-3-small` | Embedding model |
| `VECTOR_DB` | `lancedb` | Vector store (built-in) |
| `DISABLE_SWAGGER_DOCS` | `true` | Security |

---

## Storage

`storage/` is gitignored. It contains:
- `anythingllm.db` — SQLite DB (workspaces, chats, settings)
- `documents/` — processed document text
- `vector-cache/` — LanceDB vectors

Back up this folder to preserve your embeddings.
