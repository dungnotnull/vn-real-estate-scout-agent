"""VietAI ViT5-based summarization for real estate listings."""
from typing import Optional, List
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import logging

logger = logging.getLogger(__name__)


class ViT5Summarizer:
    """Vietnamese listing summarization using VietAI/vit5-large."""

    def __init__(self, model_name: str = "VietAI/vit5-large", use_model: bool = False, device: Optional[str] = None):
        """Initialize ViT5 summarizer."""
        self.model_name = model_name
        self.use_model = use_model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.pipeline = None

    def load_model(self) -> bool:
        """Load the ViT5 model and tokenizer."""
        if not self.use_model:
            logger.info("Using placeholder summarization")
            return True

        try:
            logger.info(f"Loading ViT5 model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()

            self.pipeline = pipeline(
                "summarization",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == 'cuda' else -1
            )

            logger.info("ViT5 model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load ViT5 model: {e}")
            return False

    def summarize(self, text: str, max_length: int = 150, prefix: str = "Tóm tắt bất động sản: ") -> str:
        """Generate a summary of the listing description."""
        if not self.pipeline or not self.use_model:
            return self._placeholder_summary(text)

        try:
            input_text = prefix + text

            result = self.pipeline(
                input_text,
                max_length=max_length,
                num_beams=4,
                early_stopping=True,
                do_sample=False
            )

            return result[0]['summary_text']

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return self._placeholder_summary(text)

    def _placeholder_summary(self, text: str) -> str:
        """Generate a basic summary when model is not loaded."""
        if len(text) > 150:
            return text[:147] + "..."
        return text

    def batch_summarize(self, texts: List[str], max_length: int = 150) -> List[str]:
        """Summarize multiple texts in batch."""
        return [self.summarize(text, max_length) for text in texts]

    def summarize_listings(self, listings: List[dict], language: str = "vi") -> List[str]:
        """Summarize multiple listings for reports."""
        summaries = []
        for listing in listings:
            description = listing.get('description', '')
            title = listing.get('title', '')

            # Combine title and description for better summary
            text = f"{title}. {description}" if title and description else (title or description)

            if language == "en":
                prefix = "Summarize this real estate listing: "
            else:
                prefix = "Tóm tắt bất động sản: "

            summary = self.summarize(text, prefix=prefix)
            summaries.append(summary)

        return summaries

    def __enter__(self):
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
