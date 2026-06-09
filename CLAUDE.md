# CLAUDE.md — vn-real-estate-scout

## Project Identity
- **Name**: vn-real-estate-scout
- **Tagline**: AI-powered Vietnam real estate intelligence agent — find genuine listings, skip the noise
- **Status**: Phase 0 — Research & Environment Setup
- **Folder**: `D:\Dungchan\8\`

## Core Problem
Vietnam's real estate market is flooded with ghost listings: the same property appears across 5–10 broker posts at different prices, coordinates, and contact numbers. Buyers waste weeks chasing fake ads, then discover the property was sold months ago or never existed. This agent automates the full pipeline — from wide-area scraping of all major Vietnamese platforms, through cross-reference deduplication, geospatial scoring, flood-zone checking, and draft Zalo outreach — delivering a verified "Top 5" shortlist the user can confidently visit in person.

## Architecture Summary
- **Platform**: Python 3.11+, FastAPI backend, React dashboard (optional)
- **Scraping**: `crawl4ai` + Playwright for JavaScript-rendered pages (Batdongsan, Chotot, Facebook Groups, local broker sites)
- **Storage**: Neo4j graph DB (property graph + broker relationship graph) + SQLite (user preferences, session state) + ChromaDB (vector store for RAG)
- **NLP / Vietnamese LLM**: PhoBERT for entity extraction; VietAI/vit5 for summarization; pluggable LLM backend (Claude / GPT-4o / local Ollama with Vietnamese GGUF)
- **Geo Analysis**: Google Maps Distance Matrix API + Mapbox Isochrone API + OpenStreetMap flood-risk overlay
- **Privacy**: All user data (preferences, location, budget) stored locally via AES-256 encrypted SQLite

## Key Technical Decisions
1. **Graph DB over relational DB** — Neo4j models property ↔ broker ↔ listing relationships natively, enabling cross-reference deduplication with Cypher queries instead of expensive full-table scans.
2. **PhoBERT for Vietnamese NER** — Pre-trained on Vietnamese corpus; fine-tuned for real estate entities (price, area, legal status, location landmarks). Runs entirely locally.
3. **Cross-referencing algorithm** — Cluster listings by (approximate_lat_lon ± 50m, area_m2 ± 5%, property_type). If a cluster has >2 listings with price variance >15%, flag as broker noise.
4. **Flood zone data** — Combine static historical flood maps (Vietnamese MONRE open data) with dynamic weather-API flood risk for the current season.
5. **Pluggable LLM backend** — `LLM_PROVIDER` env var: `claude` → Anthropic API; `openai` → GPT-4o; `local` → Ollama (qwen2.5:7b or gemma3:4b with Vietnamese language pack).
6. **Zalo outreach via unofficial API** — Automated first-contact messages use Zalo's web interface via Playwright; rate-limited to 5 messages/hour to avoid spam detection.
7. **Agentic RAG** — ChromaDB stores vectorized listing summaries. LLM agent retrieves semantically similar past listings to identify repriced re-listings of the same property.

## External LLM API Integrations

| Provider | Model | Config Key | Purpose |
|----------|-------|-----------|---------|
| Anthropic (Claude) | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` | Primary: Vietnamese NLU, listing summarization, negotiation drafts |
| OpenAI | gpt-4o | `OPENAI_API_KEY` | Fallback: multilingual property analysis |
| Local Ollama | qwen2.5:7b | `OLLAMA_BASE_URL` | Offline fallback: entity extraction, scoring |

## HuggingFace Models in Use

| Model ID | Purpose | Link |
|----------|---------|------|
| `vinai/phobert-base-v2` | Vietnamese NER (price, area, location, legal status extraction) | https://huggingface.co/vinai/phobert-base-v2 |
| `VietAI/vit5-large` | Listing summarization in Vietnamese | https://huggingface.co/VietAI/vit5-large |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Multilingual embeddings for RAG deduplication | https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2 |
| `rainote/vn-address-ner` | Vietnamese address parsing and geocoding normalization | https://huggingface.co/rainote/vn-address-ner |

## Active Development Tasks
- [ ] Set up crawl4ai scrapers for Batdongsan.com.vn and Chotot.com
- [ ] Build Vietnamese NER pipeline using PhoBERT
- [ ] Design Neo4j property graph schema
- [ ] Implement cross-reference deduplication algorithm
- [ ] Integrate Google Maps Distance Matrix API
- [ ] Add historical flood zone overlay (MONRE data)
- [ ] Build user preference intake form (CLI or web)
- [ ] Implement Zalo draft-message outreach module
- [ ] Wire up Claude API as primary LLM backend
- [ ] Build "Top 5" report generator

## Related Files
- `PROJECT-detail.md` — Full technical specification and architecture
- `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` — Phase-by-phase roadmap with milestones
- `SECOND-KNOWLEDGE-BRAIN.md` — Research papers, models, tools, self-update protocol
