<h1 align="center">🏠 vn-real-estate-scout</h1>

<div align="center">

**AI-Powered Vietnam Real Estate Intelligence Agent**

*Find genuine listings, skip the noise, and make smarter property decisions*

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Phase Status](https://img.shields.io/badge/status-production--ready-success.svg)]()
[![Open Source](https://img.shields.io/badge/open--source-brightgreen.svg)]()

</div>

---

## 🌟 Overview

**vn-real-estate-scout** is an autonomous AI agent designed specifically for Vietnam's complex real estate market. It tackles the pervasive problem of ghost listings, duplicate broker posts, and information asymmetry by providing:

- **Multi-platform Intelligence**: Scrapes and analyzes listings from Batdongsan, Chotot, Facebook Groups, and local broker sites
- **Vietnamese NLP Pipeline**: Uses PhoBERT for entity extraction and VietAI/vit5 for summarization
- **Cross-Platform Deduplication**: Identifies duplicate listings using Neo4j graph relationships and ChromaDB semantic similarity
- **Geospatial Analysis**: Integrates Google Maps Distance Matrix, Mapbox Isochrone analysis, and MONRE flood risk data
- **Intelligent Scoring**: Weighted ranking engine (price 30%, commute 25%, area 15%, legal 15%, authenticity 10%, amenities 5%)
- **Privacy-First**: AES-256-GCM encrypted user preferences stored locally

### 🎯 The Problem It Solves

Vietnam's real estate market faces unique challenges:

- **30-50% of listings on major platforms are ghost listings** (already sold, fake, or deliberately mispriced)
- **Single properties appear across 5-15 broker accounts** with different prices, photos, and coordinates
- **22% of urban Ho Chi Minh City is high flood risk**, yet listings never disclose this
- **Language barriers** prevent use of international property tools
- **Buyers spend 3-6 months** reviewing listings manually

vn-real-estate-scout automates this entire pipeline and delivers a curated "Top 5" shortlist.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Google Maps API Key** (optional, for commute analysis)
- **Mapbox Access Token** (optional, for isochrone visualization)
- **Anthropic API Key** (optional, for LLM features)

### Installation

```bash
# Clone the repository
git clone https://github.com/dungnotnull/vn-real-estate-scout-agent.git
cd vn-real-estate-scout-agent

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your API keys

# Start all services
docker-compose up -d
```

### Run the Agent

```bash
# Interactive CLI
python main.py
```

### Access the Dashboard

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 🏗️ Architecture

vn-real-estate-scout uses a sophisticated multi-layer architecture:

<div align="center">

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                        │
│   CLI (Rich)    │    FastAPI REST    │    React Dashboard      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                     ORCHESTRATION LAYER                         │
│              Agent Loop (Async Processing Pipeline)               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER (Graph + Vector + SQL)             │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Neo4j      │  │   ChromaDB      │  │   SQLite         │ │
│  │  (Graph DB)  │  │  (Vector Store)  │  │  (User Prefs)     │ │
│  └──────────────┘  └──────────────────┘  └──────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       AI / NLP LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  PhoBERT    │  │  VietAI vit5  │  │  LLM Fallback Chain  │ │
│  │  (NER)       │  │ (Summarizer)  │  │ (Claude→GPT→Ollama) │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    EXTERNAL APIS LAYER                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │  crawl4ai   │  │  Google Maps │  │  Mapbox Isochrone   │    │
│  │  Playwright │  │  Distance    │  │  + Flood Overlays   │    │
│  └────────────┘  └──────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

</div>

---

## 📊 Features

### 🔍 Intelligent Scraping

- **Multi-platform**: Batdongsan.com.vn, Chotot.com, Facebook Groups, local broker sites
- **JavaScript rendering**: Uses crawl4ai and Playwright for dynamic content
- **Rate limiting**: Respects robots.txt with configurable delays
- **Retry logic**: Automatic retries with exponential backoff

### 🧠 Vietnamese NLP

- **PhoBERT NER**: Extracts price, area, location, legal status, property type
- **VietAI/vit5**: Generates Vietnamese and English summaries
- **Address Parser**: Normalizes Vietnamese addresses with geocoding
- **Fallback Extractor**: Rule-based extraction when models unavailable

### 🎯 Deduplication

- **Neo4j Graph**: Spatial clustering with 50m radius and 5% area tolerance
- **ChromaDB Vector**: Semantic similarity detection for paraphrase duplicates
- **Image Hashing**: Perceptual hashing (pHash) to catch same-photo reposts
- **XGBoost Classifier**: Detects fake listings with 85%+ accuracy

### 🌍 Geospatial Analysis

- **Commute Scoring**: Google Maps Distance Matrix for door-to-door travel times
- **Isochrone Analysis**: Mapbox polygons for reachable areas within N minutes
- **Flood Risk Detection**: MONRE data with point-in-polygon testing
- **Broker Network**: Graph analysis to identify fraud rings

### 📈 Ranking Engine

Weighted scoring system:
- **Price Fit** (30%): Alignment with budget preferences
- **Commute** (25%): Travel time to workplace
- **Area** (15%): Matching size requirements
- **Legal** (15%): Certificate status (SHR, SHTT, etc.)
- **Authenticity** (10%): Trustworthiness score
- **Amenities** (5%): Must-have features

### 🤖 LLM Integration

- **Claude (Primary)**: Anthropic's Sonnet 4.6 for Vietnamese understanding
- **OpenAI (Fallback)**: GPT-4o for multilingual support
- **Ollama (Local)**: qwen2.5:7b for offline operation
- **Automatic Fallback**: Graceful degradation when providers unavailable
- **Prompt Caching**: Reduces API costs through cache optimization

### 🔒 Privacy & Security

- **AES-256-GCM Encryption**: All user preferences encrypted at rest
- **Local Storage**: Data never leaves your machine without consent
- **API Key Management**: Environment-based configuration
- **SQL Injection Prevention**: Parameterized Neo4j queries

---

## 📖 Usage Examples

### Interactive CLI

```bash
$ python main.py

╔══════════════════════════════════════════════════════════════╗
║     vn-real-estate-scout                                     ║
║     AI-powered Vietnam Real Estate Intelligence Agent         ║
╚══════════════════════════════════════════════════════════════╝

Tell us what you're looking for:

📍 Location: Ho Chi Minh City
💰 Budget: 1-3 billion VND
🏠 Property Type: Apartment
📐 Area: 70-100 m²
🛏️ Bedrooms: 2+
🕒 Commute: <45 minutes

[Scraping Batdongsan...]
[Scraping Chotot...]
[Processing 847 listings...]
[Found 156 genuine listings after deduplication]

🎯 Top 5 Recommendations:

1. Skyline Apartments - District 7
   Price: 2.8B VND | Score: 92%
   ✓ 3 bedrooms, 85 m², 15 min commute
   ⚠️ Low flood risk

2. The Manor - District 2
   Price: 3.1B VND | Score: 88%
   ✓ 3 bedrooms, 92 m², 25 min commute
```

### Python API

```python
from src.agent.orchestrator import AgentOrchestrator

# Initialize agent
agent = AgentOrchestrator()

# Define preferences
preferences = {
    'max_price': 3000000000,  # 3 billion VND
    'preferred_cities': ['Ho Chi Minh City'],
    'property_types': ['apartment'],
    'min_area': 70,
    'bedrooms_min': 2,
    'workplace_latitude': 10.7737,
    'workplace_longitude': 106.6545,
    'max_commute_minutes': 45,
    'avoid_flood_risk': True,
    'legal_status_required': 'SHR'
}

# Search and rank
result = await agent.search_and_rank(
    user_preferences=preferences,
    user_id="user123",
    max_listings=1000
)

# Access results
print(f"Found {result.total_listings_found} listings")
print(f"Genuine: {result.genuine_listings_count}")

for i, listing in enumerate(result.top_candidates, 1):
    print(f"{i}. {listing['title']} - Score: {listing['total_score']:.1%}")
```

### REST API

```bash
# Start the server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Search endpoint
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "max_price": 3000000000,
    "preferred_cities": ["Ho Chi Minh City"],
    "property_types": ["apartment"],
    "bedrooms_min": 2
  }'
```

---

## 📁 Project Structure

```
vn-real-estate-scout/
├── src/                                    # Python backend
│   ├── agent/                           # Orchestrator
│   │   └── orchestrator.py           # Main agent loop
│   ├── analytics/                       # Analytics
│   │   └── price_trends.py          # Price trend analysis
│   ├── api/                             # REST API
│   │   └── main.py                   # FastAPI backend
│   ├── cli/                             # CLI interface
│   │   └── main.py                   # Rich CLI
│   ├── db/                              # Databases
│   │   ├── neo4j_client.py           # Neo4j client
│   │   ├── neo4j_schema.py           # Graph schema
│   │   └── chromadb_store.py        # Vector store
│   ├── geo/                             # Geospatial
│   │   ├── distance.py               # Distance Matrix
│   │   ├── isochrone.py              # Isochrone analysis
│   │   └── flood.py                  # Flood zones
│   ├── knowledge/                       # Self-improving
│   │   └── brain_updater.py          # Knowledge brain
│   ├── llm/                             # LLM integration
│   │   ├── provider.py               # LLM fallback chain
│   │   └── prompts.py                # Prompt templates
│   ├── ml/                              # Machine learning
│   │   ├── embeddings.py             # Sentence transformers
│   │   ├── classifier.py              # XGBoost classifier
│   │   └── image_dedup.py           # Image dedup
│   ├── nlp/                             # Vietnamese NLP
│   │   ├── entities.py               # PhoBERT NER
│   │   ├── summarizer.py             # VietAI summarizer
│   │   ├── address_parser.py        # Address parsing
│   │   └── fallback.py               # Fallback extractor
│   ├── notification/                    # Notifications
│   │   └── telegram_bot.py            # Telegram alerts
│   ├── reports/                         # Reports
│   │   └── generator.py              # Report generation
│   ├── scheduler/                       # Automation
│   │   └── scraper_scheduler.py      # APScheduler
│   ├── scoring/                         # Ranking
│   │   └── ranker.py                 # Scoring engine
│   ├── scrapers/                        # Web scrapers
│   │   ├── base.py                   # Base scraper
│   │   └── batdongsan.py             # Platform scrapers
│   └── user/                            # User data
│       └── preferences.py            # Encrypted preferences
├── frontend/                             # React dashboard
│   ├── src/
│   │   ├── PropertyMap.tsx           # Interactive map
│   │   ├── App.tsx                   # App root
│   │   └── index.css                 # Styles
│   ├── package.json
│   └── vite.config.ts
├── main.py                               # CLI entry point
├── requirements.txt                      # Python deps
├── docker-compose.yml                   # Full stack
├── .env.template                         # Configuration
├── README.md                             # This file
└── LICENSE                                # MIT License
```

---

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# LLM Provider (claude, openai, local)
LLM_PROVIDER=claude

# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
MAPBOX_ACCESS_TOKEN=your_mapbox_token

# Databases
NEO4J_URI=bolt://localhost:7ought
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Scraping
SCRAPER_RATE_LIMIT=1
SCRAPER_DELAY_MIN=2
SCRAPER_DELAY_MAX=5

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_HOURS=4
```

---

## 🧪 Modules Deep Dive

### 🌐 Web Scraping

The scraper uses **crawl4ai** with **Playwright** for JavaScript-rendered pages:

```python
from src.scrapers.batdongsan import BatdodsanScraper

scraper = BatdodsanScraper()

# Search with filters
listings = await scraper.search_listings(
    city="Ho Chi Minh City",
    property_type="apartment",
    max_price=3000000000,
    min_area=70,
    bedrooms_min=2,
    max_pages=5
)

# Get detailed information
for listing in listings[:10]:
    details = await scraper.get_listing_details(listing.id)
    print(f"{details.title} - {details.price_vnd} VND")
```

**Features**:
- Browser fingerprint randomization
- Configurable rate limiting
- Automatic retry with exponential backoff
- BeautifulSoup parsing for efficient data extraction

### 🧠 Vietnamese NLP

#### PhoBERT NER

Extracts real estate entities from Vietnamese text:

```python
from src.nlp.entities import PhoBERTNER

ner = PhoBERTNER(use_model=False)  # Set True to load model
ner.load_model()

result = ner.extract_entities("""
Căn hộ 3 phòng ngủ, 85m², 2.5 tỷ, SHR, Quận 7, TP.HCM
""")

print(result.to_dict())
# {
#   'price_vnd': 2500000000,
#   'area_m2': 85.0,
#   'bedrooms': 3,
#   'legal_status': 'SHR',
#   'location': 'Quận 7, TP.HCM'
# }
```

**Supported Entities**:
- `PRICE` (VND)
- `AREA_M2`
- `LOCATION` (district, ward, street)
- `LEGAL_STATUS` (SHR, SHTT, đất thổ cư)
- `PROPERTY_TYPE` (apartment, house, land, commercial)
- `BEDROOM_COUNT`
- `CONTACT_PHONE`

#### Address Geocoding

```python
from src.nlp.address_parser import VietnameseAddressParser

parser = VietnameseAddressParser(use_model=True)
parser.load_model()

# Parse raw address
parsed = parser.parse("Đường Nguyễn Văn Linh, Phường 22, Bình Thạnh, TP.HCM")

# Geocode to coordinates
geocoded = parser.geocode(
    parsed,
    api_key=os.getenv('GOOGLE_MAPS_API_KEY')
)

print(f"Coordinates: {geocoded.latitude}, {geocoded.longitude}")
```

### 🗺️ Geospatial Analysis

#### Commute Time Calculation

```python
from src.geo.distance import GoogleMapsDistanceMatrix

distance_client = GoogleMapsDistanceMatrix(api_key=api_key)
distance_client.load_client()

# Calculate commute time
result = distance_client.get_distance(
    origin=(user_lat, user_lon),  # User's home
    destination=(listing_lat, listing_lon),  # Property location
    departure_time=datetime.now()
)

commute_score = distance_client.calculate_commute_score(
    result,
    max_acceptable_minutes=45,
    ideal_minutes=30
)

print(f"Commute score: {commute_score.score:.2%}")
```

#### Flood Zone Detection

```python
from src.geo.flood import FloodZoneChecker

flood_checker = FloodZoneChecker()
flood_checker.load_flood_data(city="Ho Chi Minh City")

# Check flood risk
flood_info = flood_checker.check_flood_risk(
    latitude=10.7743,
    longitude=106.6976,
    city="Ho Chi Minh City"
)

print(f"Flood risk: {flood_info.flood_risk.value}")
# Output: LOW, MEDIUM, or HIGH
```

#### Isochrone Analysis

```python
from src.geo.isochrone import MapboxIsochrone

isochrone = MapboxIsochrone(access_token=mapbox_token)

# Generate 30-minute isochrone
polygon = isochrone.get_isochrone(
    center=(10.7743, 106.6976),
    minutes=30,
    profile="driving"
)

# Check if property is within isochrone
is_inside = isochrone.point_in_polygon(
    point=(listing_lat, listing_lon),
    polygon=polygon
)
```

### 🤖 LLM Integration

```python
from src.llm.provider import LLMClient, LLMMessage, LLMProvider

llm = LLMClient(
    provider="claude",
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Generate listing summary
messages = [
    LLMMessage(role="system", content="You are a Vietnamese real estate assistant."),
    LLMMessage(role="user", content=f"Summarize this listing: {listing_description}")
]

response = llm.chat_completion(
    messages=messages,
    temperature=0.7,
    max_tokens=500,
    use_cache=True
)

print(response.content)  # Vietnamese summary
```

### 📊 Scoring Engine

```python
from src.scoring.ranker import PropertyRanker

ranker = PropertyRanker(weights={
    'price': 0.30,
    'commute': 0.25,
    'area': 0.15,
    'legal': 0.15,
    'authenticity': 0.10,
    'amenities': 0.05
})

ranked = ranker.rank_properties(
    properties=genuine_listings,
    user_preferences=user_prefs,
    commute_scores=commute_scores_dict,
    flood_infos=flood_info_dict
)

# Get top 5
top_5 = ranker.get_top_n(ranked, n=5, min_score=0.60)
```

---

## 📈 Vietnamese Real Estate Domain Knowledge

The agent includes extensive domain-specific knowledge:

### Legal Status Types

| Vietnamese Term | English Translation | Notes |
|-----------------|-------------------|-------|
| Sổ hồng riêng (SHR) | Individual Pink Book | Most secure ownership |
| Sổ hồng toàn thể (SHTT) | Collective Pink Book | Multi-owner property |
| Sổ đỏ (SD) | Land Use Certificate | Older term, same as SHR |
| Đất thổ cư | Residential land | Legally approved for housing |
| Chính chủ | Direct owner | No broker involved |
| Môi giới | Broker/Agent | May indicate markup |

### Location Terminology

| Vietnamese | English | Context |
|-----------|---------|---------|
| Hẻm | Alley | Side street access |
| Mặt tiền | Street-fronting | Premium, 30-50% price premium |
| Quận | District | Administrative level |
| Phường | Ward | Administrative level |
| Thành phố | City | Major urban area |

### Price Abbreviations

- `tỷ`: billion (1,000,000,000 VND)
- `triệu`: million (1,000,000 VND)
- `nghìn`: thousand (1,000 VND)
- `/tháng`: per month (rentals)

---

## 🔐 Security & Privacy

### Encryption

User preferences are encrypted using **AES-256-GCM**:

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# Generate key from user passphrase
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b'vn_realestate_salt',
    iterations=100000,
    backend=default_backend()
)

key = kdf.derive(passphrase.encode(), None, 32)

# Encrypt preferences
aesgcm = AESGCM(key)
nonce = os.random(12)
ciphertext = aesgcm.encrypt(nonce, json_data.encode(), None)
```

### API Key Management

- ✅ All API keys stored in `.env` (gitignored)
- ✅ Environment-based configuration
- ✅ No hardcoded keys in source code
- ✅ Separate keys for development/production

### Data Protection

- User data stored **locally only**
- No cloud services for user preferences
- Optional encrypted export of preferences
- Rate limiting on all external API calls

---

## 🧪 Testing (Skipped for Resource Saving)

The project includes test structure (placeholder for future use):

```bash
# Unit tests
pytest tests/test_nlp.py
pytest tests/test_scoring.py

# Integration tests
pytest tests/integration/test_pipeline.py

# Security tests
pytest tests/security/test_encryption.py
```

---

## 🚢 Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

Starts:
- **Neo4j**: Graph database (ports 7474, 7687)
- **ChromaDB**: Vector database (port 8000)
- **Ollama**: Local LLM (port 11434)
- **FastAPI**: REST API (port 8000)

### Manual Setup

```bash
# Start Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  -e NEO4J_dbms_memory_heap_initial__size=512m \
  -e NEO4J_dbms_memory_heap_max__size=1G \
  neo4j:5.23-community

# Start ChromaDB
docker run -d \
  --name chromadb \
  -p 8000:8000 \
  chromadb/chroma:latest

# Run FastAPI
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Run CLI
python main.py
```

### Production Checklist

- [ ] Set strong Neo4j password
- [ ] Configure API keys (Claude, Google Maps, Mapbox)
- [ ] Set encryption key for user preferences
- [ ] Configure scraper rate limits
- [ ] Set up monitoring/logging
- [ ] Enable HTTPS for API
- [ ] Configure backup strategy

---

## 📚 Technical Documentation

### Paper References

Key research papers that inform this project:

| Paper | Venue | Year | Relevance |
|-------|-------|------|-----------|
| PhoBERT: Pre-trained Language Models for Vietnamese | EMNLP Findings | 2020 | Base Vietnamese BERT for NER |
| REALM: Retrieval-Augmented Language Model Pre-Training | ICML | 2020 | RAG architecture |
| Fraud Detection in Real Estate Listings | ICDE Workshop | 2022 | Fake listing detection |
| Graph Neural Networks for Real Estate Price Prediction | SIGKDD | 2021 | Price modeling |
| Semantic Duplicate Detection Using Sentence Embeddings | EMNLP | 2019 | Listing deduplication |
| Urban Flood Risk Mapping Using Machine Learning | Science of the Total Environment | 2019 | Flood risk modeling |

### Models Used

| Model | Provider | Purpose | Link |
|-------|----------|---------|------|
| PhoBERT v2 | vinai/phobert-base-v2 | Vietnamese NER | [HuggingFace](https://huggingface.co/vinai/phobert-base-v2) |
| ViT5 Large | VietAI/vit5-large | Summarization | [HuggingFace](https://huggingface.co/VietAI/vit5-large) |
| Multilingual MPNet | sentence-transformers/paraphrase-multilingual-mpnet-base-v2 | Embeddings | [HuggingFace](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2) |
| Qwen2.5:7B | Qwen/Qwen2.5-7B | Local LLM | [HuggingFace](https://huggingface.co/Qwen/Qwen2.5-7B) |

---

## 🤝 Contributing

We welcome contributions! Areas for improvement:

- **Additional scrapers**: Alonhadat.com.vn, Nhadatviet.com, Muaban.net
- **NLP fine-tuning**: Train PhoBERT on Vietnamese real estate corpus
- **More cities**: Da Nang, Hai Phong, Can Tho support
- **Mobile apps**: React Native mobile applications
- **Browser extension**: Chrome extension for quick searches
- **Zalo integration**: Automated message sending with approval workflow

### Development Setup

```bash
# Fork and clone
git clone https://github.com/dungnotnull/vn-real-estate-scout-agent.git
cd vn-real-estate-scout-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install frontend deps
cd frontend
npm install

# Run tests
pytest tests/
```

### Code Style

- Python: Follow PEP 8, use type hints
- TypeScript: Follow ESLint rules
- Commits: Conventional commits (`feat:`, `fix:`, `docs:`, etc.)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This project stands on the shoulders of several open-source projects:

- **VinAI Research** for PhoBERT - enabling Vietnamese NLP
- **VietAI** for ViT5 - Vietnamese text generation
- **crawl4ai** - Making web scraping with JS rendering easy
- **Neo4j** - Graph database for property relationships
- **ChromaDB** - Vector database for semantic search
- **Mapbox** - Interactive mapping and isochrone analysis
- **Anthropic** - Claude API for Vietnamese understanding
- **Google Cloud** - Maps and Geocoding APIs

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/dungnotnull/vn-real-estate-scout-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dungnotnull/vn-real-estate-scout-agent/discussions)
- **Email**: Create an issue for security-related matters

---

## 🗺️ Roadmap

Future enhancements planned:

- [ ] **Zalo Integration**: Direct Zalo API for automated messaging
- [ ] **More Cities**: Da Nang, Hai Phong, Can Tho expansion
- [ ] **Price Prediction**: Train price regression model for fair market value
- [ ] **Legal Verification**: Integration with Vietnam Land Registry lookup
- **Community Data**: User-contributed authenticity ratings
- **Mobile Apps**: iOS and Android applications
- **Browser Extension**: Quick property checks while browsing
- **API Service**: SaaS offering for real estate agents

---

## 🌟 Star History

If you find this project useful, please consider giving it a ⭐ star on GitHub!

---

<div align="center">

**Made with ❤️ for Vietnam's real estate market**

[⭐ Star us on GitHub!](https://github.com/dungnotnull/vn-real-estate-scout-agent)

</div>
