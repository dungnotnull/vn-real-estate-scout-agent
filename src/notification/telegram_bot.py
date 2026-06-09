"""Telegram bot for real-time listing alerts."""
from typing import Optional, List, Dict, Any
import logging
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, Application
import asyncio

logger = logging.getLogger(__name__)


class ListingAlertBot:
    """Telegram bot for sending new matching listing alerts."""

    def __init__(self, bot_token: Optional[str] = None):
        """Initialize Telegram bot.

        Args:
            bot_token: Telegram bot token from BotFather
        """
        self.bot_token = bot_token
        self.application = None
        self.user_chats = {}  # user_id -> chat_id mapping

    async def start_bot(self):
        """Start the Telegram bot."""
        if not self.bot_token:
            logger.warning("No Telegram bot token provided")
            return

        self.application = Application.builder().token(self.bot_token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("subscribe", self._subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self._unsubscribe_command))
        self.application.add_handler(CommandHandler("preferences", self._preferences_command))

        await self.application.initialize()
        await self.application.start()

        logger.info("Telegram bot started")

    async def _start_command(self, update: Update, context):
        """Handle /start command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        self.user_chats[user_id] = chat_id

        welcome_message = """
🏠 Welcome to vn-real-estate-scout Bot!

I'll send you alerts when new listings match your criteria.

Commands:
/subscribe - Subscribe to alerts
/unsubscribe - Unsubscribe from alerts
/preferences - Set your search preferences

Let me know if you need help!
        """
        await context.bot.send_message(chat_id=chat_id, text=welcome_message)

    async def _subscribe_command(self, update: Update, context):
        """Handle /subscribe command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        self.user_chats[user_id] = chat_id

        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ You're now subscribed to listing alerts!\n\nUse /preferences to set your search criteria."
        )

    async def _unsubscribe_command(self, update: Update, context):
        """Handle /unsubscribe command."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if user_id in self.user_chats:
            del self.user_chats[user_id]

        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ You've been unsubscribed from listing alerts."
        )

    async def _preferences_command(self, update: Update, context):
        """Handle /preferences command."""
        chat_id = update.effective_chat.id

        help_text = """
📝 Set your preferences using this format:

<pre>
/set_preferences
city: Ho Chi Minh City
max_price: 3000000000
property_type: apartment
min_area: 70
bedrooms: 2
</pre>

Example:
/set_preferences city: Ho Chi Minh City, max_price: 2000000000, property_type: apartment
        """
        await context.bot.send_message(chat_id=chat_id, text=help_text, parse_mode='HTML')

    async def send_listing_alert(self, user_id: int, listing: Dict[str, Any]):
        """Send alert for new matching listing.

        Args:
            user_id: User ID to send alert to
            listing: Listing data
        """
        if user_id not in self.user_chats:
            logger.warning(f"User {user_id} not subscribed")
            return

        chat_id = self.user_chats[user_id]

        # Format message
        message = f"""
🏠 <b>New Listing Found!</b>

📍 {listing.get('address', 'Unknown Address')}
💰 {listing.get('price_vnd', 0):,.0f} VND
📐 {listing.get('area_m2', 0)} m²
🛏️ {listing.get('bedrooms', 'N/A')} bedrooms

🔗 <a href="{listing.get('url', '')}">View Listing</a>

Score: {listing.get('match_score', 0):.1%}
        """

        if self.application:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message.strip(),
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.info(f"Sent alert to user {user_id}")

    async def send_batch_alerts(self, listings: List[Dict[str, Any]], preferences: Dict[str, Any]):
        """Send alerts for multiple listings to subscribed users.

        Args:
            listings: List of matching listings
            preferences: User preferences to match against
        """
        for user_id in self.user_chats:
            for listing in listings[:5]:  # Limit to 5 per batch
                await self.send_listing_alert(user_id, listing)
                await asyncio.sleep(1)  # Rate limiting

    async def stop_bot(self):
        """Stop the Telegram bot."""
        if self.application:
            await self.application.stop()
            logger.info("Telegram bot stopped")

    def register_user(self, user_id: int, chat_id: int):
        """Register user for alerts.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
        """
        self.user_chats[user_id] = chat_id
        logger.info(f"Registered user {user_id} for alerts")

    def unregister_user(self, user_id: int):
        """Unregister user from alerts.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            logger.info(f"Unregistered user {user_id}")

    def get_subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self.user_chats)
