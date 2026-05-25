# Distribution Strategy

## The Core Problem

Remote team, IT guardrails, need to keep a research knowledge base consistent across N machines. The LLM queries happen locally (each person needs a running instance), but the embedded corpus needs to stay in sync.

---

## The Key Technical Fact: Embeddings Are Portable

AnythingLLM's vector store (LanceDB) is **file-based**. The entire `storage/` directory — SQLite DB, processed document text, and vector embeddings — is portable. You can:

```
tar -czf knowledge-base-v1.tar.gz storage/
```

Unpack it on another machine, start the container, and it works identically. No re-embedding required. **This is the foundation of the whole distribution strategy.**

---

## Option Comparison

| # | Approach | IT Risk | Cost | UX | Consistency | Verdict |
|---|---|---|---|---|---|---|
| A | Cloud VM (shared instance) | Medium | ~$10–20/mo | Best (one URL) | Perfect | Good if IT approves cloud spend |
| B | **Cloudflare Tunnel + Access** | **Low** | Free tier | Good (one URL) | Perfect | **Best long-term if approved** |
| C | Distributed containers + storage sync | Very low | Free | Fair (run locally) | Good (update script) | **Best near-term, no approvals** |
| D | AnythingLLM Cloud (Mintplex) | High (data leaves org) | ~$15+/mo | Best | Perfect | No — data leaves org |
| E | Internal server + existing corp VPN | Very low | Free (if server exists) | Fair | Perfect | Good if you have a spare server |
| F | Baked Docker image (vectors in image) | Very low | Free | Good | Perfect | Cleaner but slow updates |
| G | Tailscale mesh VPN | Low | Free (<20 users) | Fair | Perfect | IT approval required |

---

## Recommended Strategy: Two-Tier

### Tier 1 (Now) — Distributed Local + GitHub Release Sync

No IT approvals needed. Works immediately. Each person runs AnythingLLM locally. Storage snapshots are published to GitHub Releases and synced via a single script.

**How it works:**

```
Maintainer machine                    GitHub                     Teammate machine
     │                                   │                              │
     │  1. New docs added to documents/  │                              │
     │  2. GitHub Actions embeds them    │                              │
     │     (weekly cron)                 │                              │
     │─────────────────────────────────>│  3. storage.tar.gz           │
     │                                   │     published as Release     │
     │                                   │<─────────────────────────────│
     │                                   │  4. ./update.sh downloads    │
     │                                   │     + restarts container     │
```

**Requirements for teammates:**
- Docker Desktop (Mac/Windows) or Colima (Mac) — common dev tool
- Git (already have it)
- Run `./install.sh` once, `./update.sh` to stay current

**Limitations:**
- Each person has their own local instance (chat history not shared)
- Updates require running a script (not automatic, but scriptable as a cron job)
- Each machine needs its own OpenAI API key

### Tier 2 (Later) — Cloudflare Tunnel + Shared Instance

Once you have IT buy-in or a server, this is cleaner. One instance, everyone shares it, zero-config for end users.

**How it works:**
- AnythingLLM runs on one machine (internal server, your Mac, or a cheap VM)
- `cloudflared` creates an outbound-only encrypted tunnel to Cloudflare's edge
- No inbound ports opened, no VPN required, firewall untouched
- Cloudflare Access gates it to `@cds-snc.ca` email domain + MFA
- Users get a URL like `https://cx-research.yourdomain.ca`

**IT pitch:**
> "It's outbound-only traffic (like Slack or GitHub), Cloudflare handles all auth, and we can restrict it to org emails. No ports open, no firewall changes."

---

## Tier 1 Implementation Plan

### Files to Build

```
cx_anythingllm_knowledgebase/
├── .github/
│   └── workflows/
│       └── embed-and-release.yml   ← weekly auto-embed + package
├── scripts/
│   ├── install.sh                  ← one-time teammate setup
│   ├── update.sh                   ← download latest release, restart
│   └── pack-storage.sh             ← local: package storage for release
├── documents/                      ← drop new source docs here
│   └── .gitkeep
├── docker-compose.yml
├── .env.example                    ← template (no secrets)
└── README.md
```

### Update Cadence

| What | When | How |
|---|---|---|
| New documents added | On demand | Drop in `documents/`, push to main |
| Embeddings packaged | Weekly (Monday 8am) | GitHub Actions cron |
| Teammates sync | On demand or automated | `./scripts/update.sh` |

### Can embeddings actually be shipped this way?

Yes, with one caveat: the OpenAI embedding model (`text-embedding-3-small`) produces deterministic vectors — same text + same model = same vector. This means the stored vectors in LanceDB are model-specific but fully reproducible and portable. The person running `update.sh` does **not** need to re-embed anything. They're getting pre-computed vectors.

---

## Tier 2 Prerequisites Checklist

- [ ] IT approval for Cloudflare Tunnel (outbound-only, low risk)
- [ ] A domain you control (or subdomain of existing CDS domain)
- [ ] A machine that stays on (server, Mac mini, or $6/mo DigitalOcean Droplet)
- [ ] Cloudflare account (free)
- [ ] Decision: shared OpenAI key or per-user keys

---

## What "Done" Looks Like

### Tier 1 Done
- [ ] `install.sh` tested on a clean Mac
- [ ] `update.sh` downloads latest GitHub Release and restarts container
- [ ] GitHub Actions workflow runs weekly, packages storage, creates Release
- [ ] README with clear 3-step install instructions for a teammate
- [ ] At least one teammate successfully onboarded

### Tier 2 Done
- [ ] AnythingLLM accessible at a stable URL
- [ ] Login restricted to org email domain via Cloudflare Access
- [ ] Multi-user mode enabled, teammates have accounts
- [ ] Corpus auto-embeds when new docs land in `documents/` on main
