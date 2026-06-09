"""FastAPI REST backend for vn-real-estate-scout."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="vn-real-estate-scout API",
    description="Vietnam Real Estate Intelligence Agent API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SearchPreferences(BaseModel):
    """User search preferences."""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    preferred_cities: List[str] = ["Ho Chi Minh City"]
    preferred_districts: Optional[List[str]] = None
    property_types: List[str] = ["apartment"]
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None
    workplace_latitude: Optional[float] = None
    workplace_longitude: Optional[float] = None
    max_commute_minutes: Optional[int] = None
    commute_mode: str = "driving"
    must_haves: List[str] = []
    avoid_flood_risk: bool = True
    legal_status_required: Optional[str] = None
    furnished: Optional[bool] = None
    parking_required: bool = False
    verified_only: bool = True

class Listing(BaseModel):
    """Listing model."""
    listing_id: str
    property_id: str
    platform: str
    url: str
    title: str
    description: str
    price_vnd: Optional[float] = None
    area_m2: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    address: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    legal_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    posted_date: Optional[datetime] = None
    images: List[str] = []
    authenticity_score: Optional[float] = None
    match_score: Optional[float] = None

class SearchResult(BaseModel):
    """Search result model."""
    total_listings: int
    genuine_listings: int
    processing_time: float
    top_candidates: List[Listing]
    user_preferences: SearchPreferences

class FeedbackRequest(BaseModel):
    """User feedback request."""
    listing_id: str
    was_genuine: bool
    rating: Optional[int] = Field(None, ge=1, le=5)
    visited: bool = False
    purchased: bool = False
    comments: Optional[str] = None

# Dependency injection
async def get_agent():
    """Get agent instance."""
    from src.agent.orchestrator import RealEstateAgent
    return RealEstateAgent()

# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "vn-real-estate-scout API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "search": "/search",
            "listings": "/listings",
            "report": "/report",
            "feedback": "/feedback",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "neo4j": "connected",
            "chromadb": "connected",
            "llm": "available"
        }
    }

@app.post("/search", response_model=SearchResult)
async def search_properties(
    preferences: SearchPreferences,
    background_tasks: BackgroundTasks,
    max_listings: int = Query(1000, ge=1, le=5000),
    agent=Depends(get_agent)
):
    """Search for properties matching user preferences.

    Args:
        preferences: User search preferences
        background_tasks: Background tasks handler
        max_listings: Maximum listings to process
        agent: Agent instance

    Returns:
        SearchResult with top candidates
    """
    try:
        from src.agent.orchestrator import AgentResult

        # Convert to dict
        prefs_dict = preferences.model_dump()

        # Run agent
        result: AgentResult = await agent.search_and_rank(
            user_preferences=prefs_dict,
            max_listings=max_listings
        )

        # Convert to response format
        top_candidates = [
            Listing(**candidate) if not isinstance(candidate, Listing) else candidate
            for candidate in result.top_candidates
        ]

        return SearchResult(
            total_listings=result.total_listings_found,
            genuine_listings=result.genuine_listings_count,
            processing_time=result.processing_time_seconds,
            top_candidates=top_candidates,
            user_preferences=preferences
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings", response_model=List[Listing])
async def get_listings(
    platform: Optional[str] = None,
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    agent=Depends(get_agent)
):
    """Get listings with optional filters.

    Args:
        platform: Filter by platform
        city: Filter by city
        property_type: Filter by property type
        limit: Maximum results
        offset: Pagination offset
        agent: Agent instance

    Returns:
        List of listings
    """
    try:
        # Build query parameters
        filters = {}
        if platform:
            filters['platform'] = platform
        if city:
            filters['city'] = city
        if property_type:
            filters['property_type'] = property_type

        # Query database
        # This is a placeholder - implement actual DB query
        listings = await _query_listings_from_db(filters, limit, offset)

        return [Listing(**listing) for listing in listings]

    except Exception as e:
        logger.error(f"Failed to get listings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/listings/{listing_id}", response_model=Listing)
async def get_listing_details(
    listing_id: str,
    agent=Depends(get_agent)
):
    """Get detailed information for a specific listing.

    Args:
        listing_id: Listing identifier
        agent: Agent instance

    Returns:
        Listing details
    """
    try:
        # Query database
        listing_data = await _query_listing_from_db(listing_id)

        if not listing_data:
            raise HTTPException(status_code=404, detail="Listing not found")

        return Listing(**listing_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    background_tasks: BackgroundTasks
):
    """Submit user feedback for a listing.

    Args:
        feedback: User feedback data
        background_tasks: Background tasks handler

    Returns:
        Confirmation message
    """
    try:
        # Store feedback in database
        await _store_feedback(feedback)

        # Schedule model retraining in background
        background_tasks.add_task(_schedule_retraining)

        return {
            "status": "success",
            "message": "Feedback received. Thank you for helping improve our recommendations!"
        }

    except Exception as e:
        logger.error(f"Failed to store feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report/{user_id}")
async def get_report(
    user_id: str,
    format: str = Query("markdown", regex="^(markdown|pdf)$")
):
    """Generate report for user.

    Args:
        user_id: User identifier
        format: Report format (markdown or pdf)

    Returns:
        Report file or URL
    """
    try:
        from src.reports.generator import ReportGenerator
        from src.user.preferences import SecureUserStorage

        # Load user preferences
        with SecureUserStorage() as storage:
            preferences = storage.load_preferences(user_id)

        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")

        # Generate report (placeholder - needs actual implementation)
        generator = ReportGenerator()
        report_path = generator.generate_top5_report(
            ranked_properties=[],
            user_preferences=preferences.to_dict(),
            user_id=user_id
        )

        return {
            "status": "success",
            "report_path": report_path,
            "format": format
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/subscribe")
async def subscribe_alerts(
    user_id: str,
    telegram_chat_id: int,
    background_tasks: BackgroundTasks
):
    """Subscribe user to listing alerts.

    Args:
        user_id: User identifier
        telegram_chat_id: Telegram chat ID
        background_tasks: Background tasks handler

    Returns:
        Subscription confirmation
    """
    try:
        from src.notification.telegram_bot import ListingAlertBot

        # Register user for alerts
        bot = ListingAlertBot()
        bot.register_user(int(user_id), telegram_chat_id)

        return {
            "status": "success",
            "message": "Subscribed to listing alerts"
        }

    except Exception as e:
        logger.error(f"Failed to subscribe user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _query_listings_from_db(filters: Dict[str, Any], limit: int, offset: int) -> List[Dict]:
    """Query listings from database with filters."""
    # Placeholder implementation
    # In production, query Neo4j with filters
    return []

async def _query_listing_from_db(listing_id: str) -> Optional[Dict]:
    """Query single listing from database."""
    # Placeholder implementation
    return None

async def _store_feedback(feedback: FeedbackRequest):
    """Store feedback in database."""
    # Placeholder implementation
    pass

async def _schedule_retraining():
    """Schedule XGBoost model retraining."""
    # Placeholder implementation
    pass

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting vn-real-estate-scout API")

    # Initialize databases
    # Initialize connections to Neo4j, ChromaDB, etc.

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down vn-real-estate-scout API")

    # Close database connections
    # Cleanup resources
