"""Prompt templates for LLM-powered features."""
from typing import Dict, Any, List, Optional


class PromptTemplates:
    """Prompt templates for various LLM tasks."""

    # Vietnamese NER fallback extraction
    NER_EXTRACTION_VI = """Bạn là một chuyên gia trích xuất thông tin từ mô tả bất động sản bằng tiếng Việt.

Hãy trích xuất các thông tin sau từ văn bản mô tả và trả về dưới dạng JSON:
- price_vnd: Giá bằng VNĐ (số)
- area_m2: Diện tích m2 (số)
- location: Địa điểm
- bedrooms: Số phòng ngủ (số)
- legal_status: Tình trạng pháp lý (SHR, SHTT, đất thổ cư, chưa có sổ, v.v.)
- property_type: Loại bất động sản (căn hộ, nhà riêng, biệt thự, đất, v.v.)
- contact_phone: Số điện thoại liên hệ

Văn bản mô tả:
{text}

JSON:"""

    # Listing summarization
    LISTING_SUMMARY_VI = """Hãy tóm tắt bất động sản sau trong 2-3 câu tiếng Việt, tập trung vào:
1. Vị trí và diện tích
2. Giá và tính pháp lý
3. Đặc điểm chính (số phòng, nội thất, tiện ích)

{listing_details}

Tóm tắt:"""

    LISTING_SUMMARY_EN = """Summarize this Vietnamese real estate listing in 2-3 English sentences, focusing on:
1. Location and size
2. Price and legal status
3. Key features (rooms, furnishing, amenities)

{listing_details}

Summary:"""

    # Top 5 report generation
    TOP5_REPORT_VI = """Dựa trên tiêu chí tìm kiếm của người dùng và 5 bất động sản dưới đây, hãy tạo một báo cáo ngắn gọn bằng tiếng Việt.

Tiêu chí người dùng:
- Ngân sách: {budget_range} VNĐ
- Vị trí mong muốn: {preferred_location}
- Diện tích: {area_range} m2
- Thời gian di chuyển: {commute_preference} phút

5 bất động sản phù hợp nhất:
{listings}

Vui lòng:
1. Sắp xếp theo mức phù hợp (cao nhất trước)
2. Giải thích ngắn gọn tại sao mỗi bất động sản phù hợp
3. Ghi chú về rủi ro (nếu có) như nguy cơ ngập

Báo cáo:"""

    # Zalo message drafting
    ZALO_MESSAGE_VI = """Hãy soạn một tin nhắn Zalo lịch sự, chuyên nghiệp để hỏi về bất động sản này.

Thông tin bất động sản:
- Tiêu đề: {title}
- Giá: {price} VNĐ
- Diện tích: {area} m2
- Vị trí: {location}
- Liên hệ: {contact_name} - {contact_phone}

Yêu cầu:
1. Lịch sự, ngắn gọn (dưới 100 từ)
2. Hỏi về tình trạng pháp lý (Sổ đỏ/Sổ hồng)
3. Hỏi về lịch xem nhà
4. Giới thiệu bản thân (người mua thực, không phải môi giới)

Tin nhắn:"""

    # Conversational query
    CONVERSATIONAL_QUERY_VI = """Bạn là trợ lý tìm bất động sản thông minh. Người dùng hỏi câu hỏi về cơ sở dữ liệu bất động sản.

Câu hỏi: {query}

Dựa trên kết quả tìm kiếm:
{search_results}

Hãy trả lời câu hỏi bằng tiếng Việt một cách tự nhiên, chuyên nghiệp. Nếu không tìm thấy kết quả phù hợp, hãy đề xuất điều chỉnh tiêu chí.

Trả lời:"""

    # Listing explanation
    WHY_THIS_LISTING_VI = """Giải thích ngắn gọn tại sao bất động sản này phù hợp với tiêu chí của người dùng:

Tiêu chí người dùng:
- Ngân sách: {budget_range} VNĐ
- Vị trí: {preferred_location}
- Diện tích: {area_range} m2

Thông tin bất động sản:
{listing_info}

Giải thích:"""

    @staticmethod
    def format_listing_info(listing: Dict[str, Any]) -> str:
        """Format listing information for prompts.

        Args:
            listing: Listing data dictionary

        Returns:
            Formatted string
        """
        parts = [
            f"- Tiêu đề: {listing.get('title', 'N/A')}",
            f"- Giá: {listing.get('price_vnd', 0):,.0f} VNĐ" if listing.get('price_vnd') else "- Giá: Liên hệ",
            f"- Diện tích: {listing.get('area_m2', 0)} m2" if listing.get('area_m2') else "- Diện tích: N/A",
            f"- Vị trí: {listing.get('address', 'N/A')}",
            f"- Phòng ngủ: {listing.get('bedrooms', 'N/A')}" if listing.get('bedrooms') else "",
            f"- Pháp lý: {listing.get('legal_status', 'N/A')}" if listing.get('legal_status') else "",
            f"- Điểm phù hợp: {listing.get('match_score', 0):.1%}" if listing.get('match_score') else "",
        ]
        return "\n".join([p for p in parts if p])

    @staticmethod
    def format_listings_for_report(listings: List[Dict[str, Any]], with_scores: bool = True) -> str:
        """Format multiple listings for report generation.

        Args:
            listings: List of listing dictionaries
            with_scores: Include match scores

        Returns:
            Formatted string
        """
        formatted = []
        for i, listing in enumerate(listings, 1):
            parts = [
                f"BĐS #{i}:",
                PromptTemplates.format_listing_info(listing)
            ]
            if with_scores and listing.get('match_score'):
                parts.append(f"- Điểm phù hợp: {listing['match_score']:.1%}")
            formatted.append("\n".join(parts))
        return "\n\n".join(formatted)


class CacheControlManager:
    """Manage cache control headers for prompt caching.

    Claude supports prompt caching for repeated context.
    This class helps format cache control headers properly.
    """

    CACHEABLE_PREFIX = "cache_control:"
    BREAKPOINT = "ephemeral"

    @staticmethod
    def make_cache_block(text: str) -> Dict[str, Any]:
        """Create a cache-controlled text block.

        Args:
            text: Text to cache

        Returns:
            Dict with cache control headers
        """
        return {
            "type": "text",
            "text": text,
            "cache_control": {"type": CacheControlManager.BREAKPOINT}
        }

    @staticmethod
    def make_user_message_with_cache(content: str, cache_prefix: Optional[str] = None) -> Dict[str, Any]:
        """Create a user message with cache control.

        Args:
            content: Message content
            cache_prefix: Optional prefix to cache

        Returns:
            Message dict with cache control
        """
        result = {"role": "user", "content": content}
        if cache_prefix:
            result["cache_control"] = {"type": CacheControlManager.BREAKPOINT}
        return result
