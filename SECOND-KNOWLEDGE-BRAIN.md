# SECOND-KNOWLEDGE-BRAIN.md — vn-real-estate-scout

## Purpose
This file is the self-improving knowledge base for vn-real-estate-scout. It is updated weekly by a crawl4ai pipeline that monitors ArXiv, HuggingFace Papers, ACM Digital Library, and Vietnamese NLP research venues. All additions are date-stamped and appended to the Knowledge Update Log.

---

## Core Concepts & Theoretical Foundations

### 1. Agentic Retrieval-Augmented Generation (RAG)
Traditional RAG retrieves static documents at query time. Agentic RAG goes further: the agent decides *when* to retrieve, *what* to retrieve, and can issue multiple retrieval rounds before generating a final answer. For real estate search, this means the agent can iteratively narrow down candidates by retrieving listing clusters, then pulling geo data, then checking legal status — all in a single reasoning chain.

### 2. Knowledge Graphs for Real Estate
Property data is inherently relational: one address has many historical listings, one broker posts across many properties, one ward contains many streets. A knowledge graph (Neo4j) models these relationships natively. Key advantages:
- Duplicate detection via graph traversal (SIMILAR_TO edges) is O(log n) vs. O(n²) for pairwise comparison
- Broker fraud rings are detectable as dense subgraphs (community detection algorithms: Louvain, Label Propagation)
- Property provenance (chain of past listings) is preserved as a first-class data structure

### 3. Vietnamese NLP Challenges
Vietnamese is a tonal, isolating language with no spaces between words in some writing systems. Key challenges for real estate NLP:
- **Word segmentation**: "giá bán" (sale price) vs. "giábán" — tokenizers trained on general Vietnamese text fail on domain-specific compounds
- **Price abbreviations**: "2,5 tỷ" = 2.5 billion VND; "850 triệu" = 850 million VND; "15tr/tháng" = 15 million VND/month for rent
- **Area abbreviations**: "85m2", "85mét vuông", "85 m²" — all mean 85 square meters
- **Legal status shorthand**: "SHR" = Sổ hồng riêng (individual pink book); "SHTT" = Sổ hồng toàn thể; "đất thổ cư" = residential land

### 4. Geospatial Scoring for Real Estate
Multi-criteria geospatial analysis combines:
- **Isochrone analysis**: polygon of all points reachable within N minutes by a given transport mode (Mapbox API)
- **Distance matrix**: actual door-to-door travel time under peak-hour traffic conditions (Google Maps)
- **Flood risk**: historical flood extents (polygon union from multiple events) intersected with property location
- **Spatial clustering**: DBSCAN with haversine distance for grouping nearby co-listed properties

### 5. Anomaly Detection for Fake Listings
Fake listings share telltale statistical signatures:
- **Price cluster dispersion**: genuine listings cluster within ±10% of true market value; fake/broker listings show ±30–50% dispersion for the same property
- **Temporal pattern**: fake listings are reposted every 7–14 days with minor edits (price ±5%, description paragraph shuffled)
- **Image fingerprinting**: perceptual hash (pHash) similarity > 0.95 across listings from different broker accounts indicates same-property repost
- **Coordinate jitter**: brokers deliberately offset listing coordinates by 100–500m to evade de-dup tools

---

## Key Research Papers

| Title | Authors | Year | Venue | Link | Relevance |
|-------|---------|------|-------|------|-----------|
| PhoBERT: Pre-trained Language Models for Vietnamese | Dat Quoc Nguyen, Anh Tuan Nguyen | 2020 | EMNLP Findings | https://arxiv.org/abs/2003.00744 | Base Vietnamese LLM for NER and text understanding |
| ViT5: Pretrained Text-to-Text Transformer for Vietnamese Language Generation | Long Phan et al. | 2022 | NAACL | https://arxiv.org/abs/2205.06457 | Vietnamese seq2seq model for summarization |
| REALM: Retrieval-Augmented Language Model Pre-Training | Kelvin Guu et al. | 2020 | ICML | https://arxiv.org/abs/2002.08909 | Foundation paper for RAG architecture |
| Fraud Detection in Real Estate Listings Using Machine Learning | Xu et al. | 2022 | ICDE Workshop | https://doi.org/10.1109/ICDEW55742.2022 | Fake listing detection approaches |
| Graph Neural Networks for Real Estate Price Prediction | Zhang et al. | 2021 | ACM SIGKDD | https://dl.acm.org/doi/10.1145/3447548.3467203 | Graph-based price modeling |
| Cross-lingual Transfer Learning for Low-Resource NER | Wu & Dredze | 2019 | EMNLP | https://arxiv.org/abs/1902.00193 | Transfer learning strategies for Vietnamese NER with limited labeled data |
| A Survey on Knowledge Graphs: Representation, Acquisition, and Applications | Ji et al. | 2021 | IEEE TNNLS | https://arxiv.org/abs/2002.00388 | Knowledge graph construction methodology |
| Semantic Duplicate Detection Using Sentence Embeddings | Reimers & Gurevych | 2019 | EMNLP | https://arxiv.org/abs/1908.10084 | Sentence-BERT foundation for listing dedup |
| Urban Flood Risk Mapping Using Machine Learning | Tehrany et al. | 2019 | Science of the Total Environment | https://doi.org/10.1016/j.scitotenv.2019.07.103 | Flood risk modeling relevant to Vietnamese cities |
| ReAct: Synergizing Reasoning and Acting in Language Models | Yao et al. | 2022 | ICLR 2023 | https://arxiv.org/abs/2210.03629 | ReAct pattern for agentic RAG tool use |

---

## State-of-the-Art ML/DL Models

### Vietnamese NLP

| Model | HuggingFace ID | Task | Notes |
|-------|---------------|------|-------|
| PhoBERT v2 | vinai/phobert-base-v2 | Vietnamese NER, classification | Best open Vietnamese BERT; preferred for NER fine-tuning |
| ViT5 Large | VietAI/vit5-large | Seq2seq summarization | Best Vietnamese T5; use for listing summaries |
| PhoNLP | vinai/phonlp-base | NLP toolkit (NER + POS + dependency) | All-in-one Vietnamese NLP; useful for prototype |
| ViBERT | FPTAI/vibert-base-cased | General Vietnamese BERT | Alternative to PhoBERT |
| Qwen2.5-7B | Qwen/Qwen2.5-7B-Instruct | Multilingual instruction-following | Strong on Vietnamese in local Ollama mode |
| Gemma 3 4B | google/gemma-3-4b-it | Multilingual lightweight | Good Vietnamese understanding at 4B params |

### Embeddings & Retrieval

| Model | HuggingFace ID | Task | Notes |
|-------|---------------|------|-------|
| Multilingual MPNet | sentence-transformers/paraphrase-multilingual-mpnet-base-v2 | Cross-lingual sentence embeddings | Top choice for Vietnamese listing dedup |
| bge-m3 | BAAI/bge-m3 | Dense + sparse retrieval | Supports 100+ languages; strong multilingual RAG |
| Vietnamese SBERT | keepitreal/vietnamese-sbert | Vietnamese semantic similarity | Trained specifically on Vietnamese; good for property text similarity |

### Address & Geo

| Model | HuggingFace ID | Task | Notes |
|-------|---------------|------|-------|
| VN Address NER | rainote/vn-address-ner | Vietnamese address parsing | Extracts province, district, ward, street from free text |

---

## Tools, Libraries & Frameworks

| Tool | Version | GitHub / Link | Use Case |
|------|---------|--------------|---------|
| crawl4ai | 0.4+ | https://github.com/unclecode/crawl4ai | Async web scraping with JS rendering |
| Playwright | 1.44+ | https://playwright.dev/python/ | Browser automation for authenticated scraping (Facebook) |
| Neo4j Community | 5.x | https://neo4j.com/download/ | Property graph database |
| py2neo / neo4j-driver | 5.x | https://neo4j.com/docs/python-manual/ | Python Neo4j client |
| ChromaDB | 0.5+ | https://github.com/chroma-core/chroma | Vector store for semantic RAG |
| LangChain | 0.2+ | https://github.com/langchain-ai/langchain | LLM orchestration, tool binding |
| LangGraph | 0.1+ | https://github.com/langchain-ai/langgraph | Stateful agent loop with conditional branching |
| Transformers | 4.41+ | https://github.com/huggingface/transformers | PhoBERT, ViT5 inference and fine-tuning |
| sentence-transformers | 3.0+ | https://github.com/UKPLab/sentence-transformers | Listing embedding for dedup |
| XGBoost | 2.0+ | https://xgboost.readthedocs.io/ | Fake-listing classifier |
| geopandas | 0.14+ | https://geopandas.org/ | Flood shapefile processing, spatial joins |
| shapely | 2.0+ | https://shapely.readthedocs.io/ | Point-in-polygon flood zone check |
| googlemaps | 4.10+ | https://github.com/googlemaps/google-maps-services-python | Distance Matrix + Geocoding |
| APScheduler | 3.10+ | https://github.com/agronholm/apscheduler | Scraper scheduling |
| Label Studio | latest | https://github.com/HumanSignal/label-studio | NER annotation for training data |
| python-telegram-bot | 21+ | https://github.com/python-telegram-bot/python-telegram-bot | New-match alert notifications |
| FastAPI | 0.115+ | https://fastapi.tiangolo.com/ | REST API backend |
| Mapbox GL JS | 3.x | https://docs.mapbox.com/mapbox-gl-js/ | Interactive property map in React |
| imagehash | 4.3+ | https://github.com/JohannesBuchner/imagehash | Perceptual hash for photo deduplication |

---

## Self-Update Protocol

The SECOND-KNOWLEDGE-BRAIN auto-update pipeline uses crawl4ai to weekly crawl research sources and append new findings to this file.

### Target Sources

| Source | URL Pattern | Crawl Frequency |
|--------|------------|----------------|
| ArXiv cs.IR (Information Retrieval) | https://arxiv.org/list/cs.IR/recent | Weekly |
| ArXiv cs.AI | https://arxiv.org/list/cs.AI/recent | Weekly |
| ArXiv cs.CL (Computational Linguistics) | https://arxiv.org/list/cs.CL/recent | Weekly |
| HuggingFace Papers | https://huggingface.co/papers | Weekly |
| Papers With Code — Real Estate | https://paperswithcode.com/search?q=real+estate | Monthly |
| ACM Digital Library — PropTech | https://dl.acm.org/search/proceedings?query=real+estate+AI | Monthly |
| VinAI Research Blog | https://www.vinai.io/news/ | Monthly |
| VLSP Workshop (Vietnamese NLP) | https://vlsp.org.vn/ | Yearly |

### Domain-Specific Search Queries

```
ArXiv: "Vietnamese NLP" AND ("NER" OR "information extraction" OR "real estate")
ArXiv: "property listing" AND ("fake detection" OR "fraud detection" OR "duplicate detection")
ArXiv: "knowledge graph" AND "real estate" AND ("recommendation" OR "search")
ArXiv: "agentic RAG" OR "retrieval augmented generation" AND "structured data"
Google Scholar: "bất động sản" AI machine learning (Vietnamese real estate)
HuggingFace: Vietnamese language model 2024 2025
```

### Update Format (Date-Stamped Entry)

When the crawler finds a new paper, model, or tool, append a new entry to the relevant section using this format:

```markdown
### [DATE: YYYY-MM-DD] New Entry
- **Type**: Paper / Model / Tool
- **Title/Name**: ...
- **Source**: ArXiv / HuggingFace / ACM / GitHub
- **Link**: ...
- **Relevance**: One sentence explaining why this matters for vn-real-estate-scout
```

### crawl4ai Pipeline Script (Sketch)

```python
# knowledge_brain_updater.py
import asyncio
from crawl4ai import AsyncWebCrawler
from datetime import date

SOURCES = [
    "https://arxiv.org/search/?query=Vietnamese+NER+real+estate&searchtype=all&start=0",
    "https://huggingface.co/papers?q=vietnamese+language+model",
    "https://paperswithcode.com/search?q_meta=&q_type=&q=real+estate+fraud",
]

async def update_knowledge_brain():
    async with AsyncWebCrawler() as crawler:
        for url in SOURCES:
            result = await crawler.arun(url=url)
            # Extract paper titles, authors, links using LLM extraction
            # Append date-stamped entries to SECOND-KNOWLEDGE-BRAIN.md
            pass

if __name__ == "__main__":
    asyncio.run(update_knowledge_brain())
```

### Schedule
- **Frequency**: Weekly, every Sunday at 02:00 local time
- **Trigger**: APScheduler cron job inside the main agent process
- **On failure**: Log error, skip week, do not crash main agent

---

## Knowledge Update Log

| Date | Source | Entry Added | Type |
|------|--------|------------|------|
| 2026-06-03 | Manual (initial population) | PhoBERT, ViT5, crawl4ai, Neo4j, ChromaDB, core papers | Seed |

---

## Vietnamese Real Estate Market Data Sources

| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|-----------------|
| Batdongsan.com.vn | https://batdongsan.com.vn | Listings (buy + rent) | Real-time |
| Chotot.com | https://chotot.com/mua-ban-bat-dong-san | Listings (secondary market) | Real-time |
| Alonhadat.com.vn | https://alonhadat.com.vn | Listings (buy + rent) | Real-time |
| Nhadatviet.com | https://nhadatviet.com | Listings (buy + rent) | Real-time |
| Muaban.net | https://muaban.net/bat-dong-san | Listings (classified) | Real-time |
| Vietnam Statistics Office | https://www.gso.gov.vn | Market statistics | Quarterly |
| VARS (Vietnam Association of Realtors) | https://vars.org.vn | Market reports | Quarterly |
| CBRE Vietnam | https://www.cbre.com/vietnam | Investment market data | Quarterly |
| MONRE (Flood data) | https://www.monre.gov.vn | Flood risk shapefiles | Yearly |
| World Bank Vietnam Urban Data | https://datacatalog.worldbank.org | Urban flood risk GIS | Periodic |

---

## Domain Glossary — Vietnamese Real Estate Terms

| Vietnamese Term | English Translation | Notes |
|-----------------|-------------------|-------|
| Sổ đỏ (sổ hồng) | Land Use Rights Certificate | Red/pink book; most important legal document for Vietnamese property |
| Sổ hồng riêng (SHR) | Individual Pink Book | Individual title, most secure ownership type |
| Đất thổ cư | Residential land | Legally approved for housing construction |
| Chính chủ | Direct owner (no broker) | Most trusted listing type; owner sells directly |
| Môi giới | Broker/Agent | Intermediary; listings marked "môi giới" often have inflated prices |
| Tin ảo | Ghost listing / Fake listing | Property that doesn't exist or is already sold |
| Giá thỏa thuận | Negotiable price | Listed price is not final |
| Nội thất cơ bản | Basic furnishings | Partial furnishings included |
| Nội thất đầy đủ | Fully furnished | All furnishings included |
| Rốn ngập | Flood basin / Flood-prone area | Colloquial term for regularly flooded low-lying zones |
| Hẻm | Alley | Side street or alley access (important for Vietnamese urban properties) |
| Mặt tiền | Street-facing frontage | Premium property type; street-facing units command 30–50% premium |
| Pháp lý | Legal status | Covers land use rights certificate, construction permit, ownership disputes |
| Diện tích sử dụng | Usable floor area | Net area, excludes walls and common areas |
| Diện tích đất | Land area | Total land plot size |
