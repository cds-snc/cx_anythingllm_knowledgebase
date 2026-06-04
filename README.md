# CX Knowledge Base

A local AI assistant pre-loaded with native plants documentation for British Columbia. Ask it questions in plain English — it answers only from the embedded documents, so it won't make things up.

---

## Quick start with GitHub Codespaces (recommended)

No installs needed. Runs entirely in your browser.

**One-time setup (done by a team lead, once for the whole team):**
- Go to the repo on GitHub > **Settings** > **Secrets and variables** > **Codespaces**
- Add two secrets: `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` (ask your team lead for these values)

**To launch:**
1. Go to the repo on **github.com**
2. Click the green **Code** button > **Codespaces** tab > **Create codespace on main**
3. Wait 2-3 minutes — the knowledge base downloads and the app starts automatically
4. A browser tab opens to the AnythingLLM UI when it's ready
5. Create an account when prompted (stored in the Codespace, not sent anywhere)
6. Select **CX Knowledge Base** from the workspace list and start asking questions

The knowledge base updates automatically every time the Codespace starts. No manual steps needed.

> **If the browser tab opens to a blank page**, wait 30-60 seconds and refresh. The app is still starting up.

---

## Local setup (alternative)

If you prefer to run it on your Mac instead of Codespaces, follow the steps below.

### What you'll need

- A Mac (macOS 13 Ventura or later)
- Your Azure OpenAI credentials — two values, ask your team lead:
  - **API key** — looks like `a1b2c3d4e5f6...`
  - **Endpoint URL** — looks like `https://cds-platform-ai.openai.azure.com/`
- About 10–15 minutes for the first-time setup

That's it. No developer tools, no accounts, no coding required.

---

## One-time setup

### Step 1 — Install Docker Desktop

Docker runs the AI assistant on your Mac. You only do this once.

1. Go to **https://www.docker.com/products/docker-desktop/**
2. Click **Download for Mac** — choose **Apple Chip** if your Mac is M1/M2/M3/M4, or **Intel Chip** if it's older
3. Open the downloaded `.dmg` file and drag Docker to your Applications folder
4. Open **Docker** from your Applications folder (or use Spotlight: press `⌘ Space`, type `Docker`, press Enter)
5. A whale icon will appear in your menu bar — wait until it **stops animating**

Docker Desktop is now running. You can leave it running in the background.

---

### Step 2 — Open Terminal

Terminal lets you type commands to your Mac. Don't worry — you'll only need to paste a few lines.

Press `⌘ Space` (Command + Space), type **Terminal**, press **Enter**.

A window with a blinking cursor will open. Keep it open for the next steps.

---

### Step 3 — Get the project files

Paste this into Terminal and press **Enter**:

```
git clone https://github.com/cds-snc/cx_anythingllm_knowledgebase.git
cd cx_anythingllm_knowledgebase
```

> **If a popup appears** asking to install developer tools — click **Install**, wait for it to finish (a few minutes), then paste the command again.

---

### Step 4 — Run setup

Paste this into Terminal and press **Enter**:

```
bash scripts/install.sh
```

The script will ask you **two questions** — paste your credentials when prompted:

1. **Azure OpenAI API key** → paste your key, press Enter
2. **Azure endpoint URL** → paste the URL, press Enter

The script then downloads everything and starts the assistant. This takes **2–5 minutes** the first time (it's downloading a ~2 GB container image).

When you see **Setup complete!** you're done.

---

### Step 5 — Open the assistant

Go to **http://localhost:3001** in your browser.

- **Create an account** when prompted — this is saved only on your Mac, not sent anywhere
- Select **CX Knowledge Base** from the workspace list
- Type your question and press **Enter**

---

## Stopping and starting

**When you're done for the day**, run in Terminal:
```
docker compose down
```

**To start it again** the next day:
1. Make sure Docker Desktop is open (whale in menu bar)
2. Run in Terminal (you need to `cd` to the project folder first):
```
cd cx_anythingllm_knowledgebase
docker compose up -d
```
Then go to http://localhost:3001.

---

## Getting document updates

When new documents have been added to the knowledge base:

```
bash scripts/update.sh
```

Run this from inside the `cx_anythingllm_knowledgebase` folder.

---

## Troubleshooting

**"Cannot connect to Docker daemon" or "Docker is not running"**  
→ Open Docker Desktop from your Applications folder. Wait for the whale icon in the menu bar to stop animating, then try again.

**Popup asking to install developer tools (Xcode Command Line Tools)**  
→ Click Install and let it finish. Then re-run the command that prompted it.

**The page at http://localhost:3001 won't load**  
→ Wait 60 seconds and try again. The container takes time to start.  
→ If it still doesn't work, run `docker compose up -d` and wait another minute.

**"git: command not found"**  
→ This shouldn't happen if you completed Step 3 above. If it does, run the `git clone` command again — the developer tools popup should appear.

**You already ran setup before and need to redo it**  
→ Just run `bash scripts/install.sh` again from inside the project folder.

---

## Technical reference

<details>
<summary>For developers — expand for technical details</summary>

### How it works

When you ask a question:

1. Your question is converted to a vector (a numerical fingerprint) by a small model running inside the container — no API call, no cost.
2. That vector is compared against the pre-embedded document library using LanceDB, stored in `./storage/`.
3. The most relevant passages are retrieved and sent, along with your question, to **Azure OpenAI gpt-4o** (CDS org endpoint).
4. gpt-4o answers using only those passages. The workspace is in **Query mode** — it will say "I don't know" rather than guess if the answer isn't in the documents.

Everything except the final LLM call runs locally. Document vectors never leave your machine.

### Stack

| Component | Technology |
|-----------|------------|
| App | AnythingLLM v1.12+ (Docker) |
| LLM | Azure OpenAI gpt-4o (CDS org endpoint) |
| Embedder | Xenova/all-MiniLM-L6-v2 (native, in-container, free) |
| Vector DB | LanceDB (file-based, `./storage/lancedb/`) |
| Database | SQLite (`./storage/anythingllm.db`) |

### Corpus

20 markdown documents in `docs/corpus-md/`:
- 16 CRD infosheets (shade, sun, seashore, rock garden, meadow, butterfly, wildlife, edible plants, etc.) — OCR'd from PDF for clean text extraction
- `nativeplantsguide.md` — comprehensive low-maintenance native planting guide
- 3 additional topic guides (moist/wet sites, Garry Oak ecosystem, plant ground covers)

All documents are embedded with 384-dimension vectors (all-MiniLM-L6-v2).
Reranker: `NativeEmbeddingReranker` (ms-marco-MiniLM-L-6-v2), enabled via `vectorSearchMode: "rerank"`.

### Environment variables

See `.env.example`. Critical vars:

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Base URL, e.g. `https://cds-platform-ai.openai.azure.com/` |
| `AZURE_OPENAI_MODEL_PREF` | Deployment name, default `gpt-4o` |
| `EMBEDDING_ENGINE` | Set to `native` (free, in-container) |
| `VECTOR_DB` | Set to `lancedb` |
| `ANYWHERE_API_KEY` | AnythingLLM API key (for script/API use) |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install.sh` | Fresh install: interactive setup, pulls image, loads corpus snapshot |
| `scripts/update.sh` | Pull latest corpus snapshot from GitHub Releases and restart |
| `scripts/convert_documents.py` | Convert PDF/DOCX/XLSX in `documents/` to markdown (run by CI) |
| `scripts/pack-storage.sh <tag>` | Package current `storage/` as a release tarball |
| `scripts/test.sh` | End-to-end test suite (14 checks) |
| `scripts/eval_rag.py` | RAG quality evaluation using openevals (correctness, groundedness, helpfulness) |

### Running tests

```bash
bash scripts/test.sh
```

All 14 checks must pass before releasing. Tests cover: container health, API auth, workspace state, Azure LLM config, 3 live query validations, and anti-hallucination mode.

### Evaluating RAG quality

Assess the quality of the RAG system's answers using LLM-as-judge evaluations:

```bash
python3 scripts/eval_rag.py              # Full evaluation (5 test cases, 3 dimensions each)
python3 scripts/eval_rag.py --dry-run    # Test connectivity only
```

The evaluator measures:
- **Correctness** — does the answer match expected facts?
- **Groundedness** — is the answer supported by retrieved context?
- **Helpfulness** — is the response useful and complete?

Uses OpenEvals (LangChain) with Azure OpenAI as the judge model. Requires `.env` to have `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` set.

### Adding new documents

Drop a PDF, DOCX, or XLSX file into `documents/` and push to `main`. GitHub Actions will automatically:
1. Convert it to markdown (via `markitdown`)
2. Embed the markdown into the RAG
3. Publish a new release

Everyone else gets the update automatically on their next Codespace start or `bash scripts/update.sh`.

### Manual release

```bash
bash scripts/pack-storage.sh v$(date +%Y-%m-%d)
# Run the gh release create command it outputs
```

### API access

```bash
curl -X POST http://localhost:3001/api/v1/workspace/cx-knowledge-base/chat \
  -H "Authorization: Bearer $ANYWHERE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"What native plants grow well in shade?","mode":"query"}'
```

</details>
