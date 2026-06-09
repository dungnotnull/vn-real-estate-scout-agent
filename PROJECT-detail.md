# PROJECT-detail.md — vn-real-estate-scout

## Executive Summary
vn-real-estate-scout is an autonomous AI agent that continuously monitors Vietnam's fragmented real estate market, filters out fraudulent and duplicate broker listings, performs multi-layer geospatial analysis, and delivers a curated, verified shortlist of properties that precisely match user-defined criteria. It handles the full pipeline from raw web scraping to draft Zalo negotiation messages, saving buyers and renters weeks of manual searching in one of Southeast Asia's noisiest property markets.

---

## Problem Statement

Vietnam's residential real estate market is the 6th largest in Southeast Asia by transaction volume, yet it operates with near-zero transparency:

- **Ghost listings dominate major platforms**: Independent analyses of Batdongsan.com.vn estimate that 30–50% of active listings are either sold, duplicate broker reposts, or intentionally mispriced to generate lead inquiries.
- **Cross-platform broker noise**: A single property in Ho Chi Minh City is routinely posted by 5–15 different broker accounts across Batdongsan, Chotot, Facebook Groups, and personal agency websites — each with slightly different prices, photos, and coordinates.
- **Flood risk is invisible to most buyers**: ~22% of Ho Chi Minh City's urban area is classified as high flood risk by the World Bank (2020), yet property listings never disclose this. Buyers discover it only after purchase.
- **Language barrier for tools**: All major international property search tools (Zillow, Rightmove) do not support Vietnamese, and their algorithms are calibrated for Western market structures.
- **Time cost**: A typical Vietnamese home buyer spends 3–6 months and 200+ hours on manual listing review before making a purchase decision (VARS 2023 survey estimate).

**The gap**: No existing tool combines Vietnamese NLP, cross-platform deduplication, real-time geospatial scoring, and flood-risk checking into one automated workflow.

---

## Target Users & Use Cases

| User Type | Use Case | Pain Point Solved |
|-----------|----------|-----------------|
| First-time homebuyer (25–40yo urban) | Find apartment under 3 billion VND in District 7, within 30 min commute to tech park | Too many fake/duplicate listings on Batdongsan |
| Expat relocating to Vietnam | Find 3-month rental near international school in Thu Duc | Language barrier + scam listings targeting foreigners |
| Property investor | Monitor price trends in specific ward, identify underpriced listings | No reliable price history data at ward level |
| Real estate researcher | Analyze supply/demand ratios per district | No structured public dataset of active listings |
| Corporate HR / Relocation team | Source housing options for incoming employees | No API for Vietnamese property data |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                        │
│          CLI (rich) │ FastAPI REST │ React Dashboard            │
└──────────────────────────────┬──────────────────────────────────┘
                               │ User Preferences (budget, location,
                               │ area, commute target, must-haves)
┌──────────────────────────────▼──────────────────────────────────┐
│                     ORCHESTRATION LAYER                         │
│            AgentLoop (LangGraph / custom async loop)            │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│   │ Scrape Agent │  │ Dedup Agent  │  │  Geo-Score Agent    │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘  │
│          │                 │                      │             │
└──────────┼─────────────────┼──────────────────────┼────────────┘
           │                 │                      │
┌──────────▼─────────────────▼──────────────────────▼────────────┐
│                      DATA LAYER                                 │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Neo4j Graph  │  │  ChromaDB Vector │  │  SQLite (local)  │ │
│  │  (listings,   │  │  (RAG + semantic  │  │  (user prefs,   │ │
│  │  brokers,     │  │   dedup)          │  │  session, cache) │ │
│  │  properties)  │  └──────────────────┘  └──────────────────┘ │
│  └───────────────┘                                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       AI / NLP LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ PhoBERT NER  │  │  VietAI vit5 │  │  LLM Backend         │  │
│  │ (entity ext) │  │  (summarize) │  │  Claude/GPT-4o/Ollama│  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    EXTERNAL SERVICES LAYER                      │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ crawl4ai   │  │ Google Maps  │  │  Mapbox Isochrone    │    │
│  │ Playwright │  │ Distance API │  │  + OSM Flood Layer   │    │
│  └────────────┘  └──────────────┘  └──────────────────────┘    │
│  Sources: Batdongsan │ Chotot │ Facebook Groups │ Local brokers  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Source / Notes |
|-----------|-----------|---------------|
| Web scraping | crawl4ai 0.4+ | https://github.com/unclecode/crawl4ai |
| Browser automation | Playwright (Python) | JavaScript-rendered pages |
| Graph database | Neo4j Community 5.x | Property + broker relationship graph |
| Vector store | ChromaDB 0.5+ | Semantic deduplication + RAG |
| Local relational DB | SQLite + SQLAlchemy | User prefs, cache, session state |
| Vietnamese NER | vinai/phobert-base-v2 | Fine-tuned for RE entities |
| Summarization | VietAI/vit5-large | Vietnamese abstractive summary |
| Embeddings | sentence-transformers/paraphrase-multilingual-mpnet-base-v2 | 768-dim multilingual |
| Address parsing | rainote/vn-address-ner | Vietnamese address normalization |
| LLM orchestration | LangGraph + LangChain | Agent loop, tool calls |
| Primary LLM | Claude claude-sonnet-4-6 via Anthropic SDK | Vietnamese NLU, report generation |
| Fallback LLM | GPT-4o via OpenAI SDK | Multilingual fallback |
| Offline LLM | Ollama + qwen2.5:7b | Local air-gap mode |
| Geo API | Google Maps Distance Matrix | Commute time calculation |
| Isochrone | Mapbox API | Reachable-zone polygon |
| Flood data | Vietnamese MONRE open data + OpenStreetMap flood layer | Static + historical |
| Encryption | Python cryptography (AES-256-GCM) | User data at rest |
| API backend | FastAPI 0.115+ | REST endpoints for dashboard |
| UI (optional) | React 18 + Vite | Property map dashboard |

---

## ML/DL Models

### PhoBERT — Vietnamese NER (Primary)
- **Model**: `vinai/phobert-base-v2`
- **Task**: Named Entity Recognition for real estate entities
- **Entities extracted**: `PRICE`, `AREA_M2`, `LOCATION`, `LEGAL_STATUS`, `PROPERTY_TYPE`, `BEDROOM_COUNT`, `CONTACT_INFO`
- **Fine-tuning**: Required — no off-the-shelf RE-domain NER exists for Vietnamese. Fine-tune on 5,000 labeled listing descriptions (manually annotated from Batdongsan corpus).
- **Training data**: Export raw listing text from scraper, annotate with Label Studio, convert to IOB2 format.
- **Estimated training time**: 2–4 hours on single RTX 3060

### VietAI/vit5-large — Summarization
- **Model**: `VietAI/vit5-large`
- **Task**: Generate 2–3 sentence Vietnamese summary of listing details for display
- **Fine-tuning**: Not required; use zero-shot with prefix prompt "Tóm tắt bất động sản:"

### Multilingual Sentence Embeddings — Deduplication
- **Model**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- **Task**: Encode listing descriptions to 768-dim vectors; cosine similarity > 0.92 triggers duplicate flagging
- **Fine-tuning**: Not required

### Anomaly Scoring — Fake Listing Detector
- **Model**: Custom XGBoost classifier trained on features: price_variance_in_cluster, listing_age_days, broker_account_age, image_hash_match_count, coordinate_jitter_meters
- **Labels**: `GENUINE` / `SUSPECTED_FAKE` / `CONFIRMED_DUPLICATE`

---

## External LLM API Integration

The `LLM_PROVIDER` environment variable controls which backend is active:

```python
LLM_PROVIDER=claude      # ANTHROPIC_API_KEY required
LLM_PROVIDER=openai      # OPENAI_API_KEY required
LLM_PROVIDER=local       # OLLAMA_BASE_URL=http://localhost:11434
```

**Graceful fallback chain**: `claude` → `openai` → `local`

**LLM tasks**:
1. Parse ambiguous Vietnamese listing descriptions (slang, abbreviations: "SHR", "chính chủ", "nội thất cơ bản")
2. Extract structured JSON from free-text listings when PhoBERT NER confidence < 0.75
3. Generate personalized "Top 5" report with user-friendly Vietnamese/English explanations
4. Draft polite Zalo first-contact messages asking about legal status and viewing availability
5. Answer user natural-language queries about the property database ("Có căn nào dưới 2 tỷ gần Phú Mỹ Hưng không?")

---

## Feature Specification

### MVP Features
- [ ] Scraper: Batdongsan.com.vn (buy + rent listings, HCMC + Hanoi)
- [ ] Scraper: Chotot.com (used property listings)
- [ ] Vietnamese NER pipeline: extract price, area, location, legal status
- [ ] Cross-reference deduplication: cluster by geo + area + type, flag duplicates
- [ ] User preference intake: CLI questionnaire (budget, location, area range, must-haves)
- [ ] Commute time calculation: Google Maps Distance Matrix to user's workplace
- [ ] Flood zone check: static overlay from MONRE data
- [ ] Ranking engine: weighted score (price fit, commute, area, legal clarity, authenticity)
- [ ] Top 5 report: PDF/Markdown output with scores, summaries, contact info
- [ ] AES-256 encryption for user preference file

### Advanced Features
- [ ] Scraper: Facebook Groups (BĐS TPHCM, Muabannhadat groups)
- [ ] Scraper: Local broker websites (Alonhadat, Nhadatviet, Muaban.net)
- [ ] Real-time price trend analysis per ward/district (rolling 30-day window)
- [ ] Zalo auto-outreach: draft + send first-contact messages, log replies
- [ ] Neo4j broker network analysis: identify serial fake-listing brokers by account linkage graph
- [ ] Dynamic flood risk: integrate weather API for seasonal flood probability
- [ ] Mobile-first React dashboard with interactive map (Mapbox)
- [ ] Price history chart per property address cluster
- [ ] Legal document checklist generator (Sổ đỏ / Sổ hồng verification steps)
- [ ] Multi-city support: Da Nang, Hai Phong, Can Tho
- [ ] Export to Google Sheets / Notion
- [ ] Telegram/Zalo bot interface for alerts ("New match found!")

---

## Full E2E Data Flow

1. **User onboarding**: User fills preference form → stored encrypted in SQLite (`user_profile.db`)
2. **Scrape trigger**: Scheduler (APScheduler, every 4 hours) or manual trigger starts crawl4ai scraper
3. **Raw data ingest**: Scrapers fetch listings from Batdongsan / Chotot / Facebook; raw HTML/JSON saved to staging table
4. **NER extraction**: PhoBERT processes each listing text → extracts `{price, area_m2, address_raw, legal_status, property_type, contact}`
5. **Address normalization**: `rainote/vn-address-ner` parses Vietnamese address → geocoded via Google Maps Geocoding API → `(lat, lon)`
6. **Graph insertion**: New property node inserted into Neo4j with all attributes; `LISTED_BY` edge to broker node; `SIMILAR_TO` edges computed via embedding cosine similarity
7. **Deduplication**: Cypher query clusters nodes within 50m radius + ±5% area → XGBoost classifier scores each cluster for authenticity
8. **Geo scoring**: Distance Matrix API calculates commute time to user's workplace; Mapbox isochrone checks if property is inside user's reachable zone
9. **Flood zone check**: Point-in-polygon test against MONRE flood shapefile → `flood_risk: LOW / MEDIUM / HIGH`
10. **Preference matching**: Weighted scoring function combines: price fit (30%), commute (25%), area fit (15%), legal status (15%), authenticity score (10%), amenities (5%)
11. **Top 5 selection**: Top 5 scoring genuine listings extracted from Neo4j
12. **Report generation**: LLM (Claude API) generates natural-language summary for each listing; vit5 generates Vietnamese abstract; combined into PDF/Markdown report
13. **Outreach drafts**: For each Top 5 listing, LLM drafts a Zalo first-contact message; user reviews and approves before send
14. **Send & monitor**: Playwright sends approved Zalo messages; replies captured and added to listing node in Neo4j

---

## Privacy & Security

| Concern | Mitigation |
|---------|-----------|
| User home address / workplace location | AES-256-GCM encrypted in SQLite; key derived from user passphrase via PBKDF2 |
| Budget and financial preferences | Stored only locally; never sent to external service without explicit consent |
| Scraping ToS compliance | Respect `robots.txt`; rate-limit to 1 request/3s per domain; randomize user-agent |
| Zalo outreach | Human-in-the-loop: user must approve each message before send; no bulk unsolicited messages |
| Broker personal data | Broker names/phones visible in listings are public data; not stored beyond session unless needed for Neo4j fraud graph |
| API key security | All keys in `.env` file; `.env` listed in `.gitignore`; never logged |

---

## Key Python Dependencies

```
crawl4ai>=0.4.0
playwright>=1.44.0
neo4j>=5.20.0
chromadb>=0.5.0
sqlalchemy>=2.0.0
langchain>=0.2.0
langgraph>=0.1.0
anthropic>=0.28.0
openai>=1.30.0
transformers>=4.41.0
sentence-transformers>=3.0.0
torch>=2.3.0
xgboost>=2.0.0
scikit-learn>=1.5.0
googlemaps>=4.10.0
shapely>=2.0.0
geopandas>=0.14.0
fastapi>=0.115.0
uvicorn>=0.30.0
pydantic>=2.7.0
cryptography>=42.0.0
apscheduler>=3.10.0
rich>=13.7.0
python-dotenv>=1.0.0
reportlab>=4.2.0
```

---

## Improvement Suggestions (Beyond Original Idea)

1. **Broker reputation scoring**: Build a persistent reputation score for each broker in the Neo4j graph, penalizing accounts with high historical fake-listing rates. Surface this score to users.
2. **Price prediction model**: Train a Vietnamese RE price regression model (XGBoost + PhoBERT embeddings) on 6 months of scraped data to predict fair market value vs. listed price.
3. **Legal status verification workflow**: Integrate with Vietnam Land Registry public portal to auto-verify Sổ đỏ/Sổ hồng number existence (read-only public lookup).
4. **Air quality and noise pollution layer**: Add PM2.5 monitoring station data (IQAIR API) and OSM land-use analysis to score neighborhood livability beyond flood risk.
5. **School district mapping**: For families, overlay school quality rankings (Vietnamese Ministry of Education data) as an additional location scoring factor.
6. **Rental yield calculator**: For investor use case, estimate gross rental yield from listing price and comparable rental data in the same cluster.
7. **WhatsApp/Viber fallback**: Many sellers are only reachable on WhatsApp or Viber; add parallel outreach channels.
8. **Comparative market analysis (CMA) report**: Generate a full CMA PDF for any target address, comparable to what a licensed agent would produce, to support negotiation.
9. **Alert system**: Push notifications via Telegram bot when a new listing matching user criteria appears within 30 minutes of posting (high-value listings sell fast in Vietnam).
10. **Community data enrichment**: Allow multiple users (opt-in) to contribute anonymized viewing experience notes back to the system, creating a crowd-sourced authenticity layer.
