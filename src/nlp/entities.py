"""PhoBERT-based Vietnamese NER for real estate entity extraction."""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Named entity extracted from Vietnamese listing text."""
    entity_type: str
    text: str
    value: Any
    confidence: float
    start: int
    end: int


@dataclass
class NERResult:
    """Complete NER extraction result for a listing."""
    price_vnd: Optional[float] = None
    area_m2: Optional[float] = None
    location: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    legal_status: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    entities: List[ExtractedEntity] = None
    model_confidence: float = 0.0

    def __post_init__(self):
        if self.entities is None:
            self.entities = []

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}

    def has_high_confidence(self, threshold: float = 0.75) -> bool:
        return self.model_confidence >= threshold


class PhoBERTNER:
    """Vietnamese NER using PhoBERT model with real model loading."""

    ENTITY_LABELS = {
        'B-PRICE', 'I-PRICE',
        'B-AREA', 'I-AREA',
        'B-LOCATION', 'I-LOCATION',
        'B-LEGAL', 'I-LEGAL',
        'B-TYPE', 'I-TYPE',
        'B-BEDROOM', 'I-BEDROOM',
        'B-BATHROOM', 'I-BATHROOM',
        'B-FLOOR', 'I-FLOOR',
        'B-PHONE', 'I-PHONE',
        'B-NAME', 'I-NAME',
        'O'
    }

    LEGAL_STATUS_MAP = {
        'sổ hồng riêng': 'SHR',
        'shr': 'SHR',
        'sổ hồng toàn thể': 'SHTT',
        'shtt': 'SHTT',
        'sổ đỏ': 'SD',
        'đất thổ cư': 'dat_tho_cu',
        'thổ cư': 'dat_tho_cu',
        'chưa có sổ': 'chua_co_so',
    }

    PROPERTY_TYPE_MAP = {
        'căn hộ': 'apartment',
        'chung cư': 'apartment',
        'nhà riêng': 'house',
        'nhà phố': 'house',
        'biệt thự': 'villa',
        'đất': 'land',
        'dat': 'land',
        'mặt bằng': 'commercial',
        'văn phòng': 'commercial',
    }

    def __init__(self, model_name: str = "vinai/phobert-base-v2", use_fine_tuned: bool = False, device: Optional[str] = None):
        self.model_name = model_name
        self.use_fine_tuned = use_fine_tuned
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.pipeline = None

    def load_model(self) -> bool:
        """Load the PhoBERT model and tokenizer."""
        try:
            logger.info(f"Loading PhoBERT model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # Load fine-tuned model if available
            if self.use_fine_tuned:
                from src.config import MODELS_DIR
                model_path = MODELS_DIR / "phobert_re_ner"
                if model_path.exists():
                    self.model = AutoModelForTokenClassification.from_pretrained(model_path)
                    logger.info(f"Loaded fine-tuned model from {model_path}")
                else:
                    logger.warning(f"Fine-tuned model not found at {model_path}, using base model")
                    self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            else:
                # Use base model with token classification head
                self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)

            self.model.to(self.device)
            self.model.eval()

            # Create NER pipeline
            self.pipeline = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == 'cuda' else -1,
                aggregation_strategy="simple"
            )

            logger.info("PhoBERT model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            return False

    def extract_entities(self, text: str) -> NERResult:
        """Extract real estate entities from Vietnamese text."""
        if not self.pipeline:
            logger.warning("Pipeline not loaded, using fallback extractor")
            return self._fallback_extract(text)

        try:
            entities = self.pipeline(text)

            result = NERResult()
            result.entities = []
            confidences = []

            for entity in entities:
                entity_type = entity.get('entity_group', entity.get('entity', 'O'))
                entity_text = entity.get('word', '')
                confidence = entity.get('score', 0.0)

                # Map entity types
                if 'PRICE' in entity_type:
                    result.price_vnd = self._parse_price(entity_text)
                elif 'AREA' in entity_type:
                    result.area_m2 = self._parse_area(entity_text)
                elif 'LOCATION' in entity_type:
                    result.location = entity_text
                elif 'LEGAL' in entity_type:
                    result.legal_status = self._normalize_legal_status(entity_text)
                elif 'TYPE' in entity_type:
                    result.property_type = self._normalize_property_type(entity_text)
                elif 'BEDROOM' in entity_type:
                    result.bedrooms = self._parse_number(entity_text)
                elif 'BATHROOM' in entity_type:
                    result.bathrooms = self._parse_number(entity_text)
                elif 'FLOOR' in entity_type:
                    result.floor = self._parse_number(entity_text)
                elif 'PHONE' in entity_type:
                    result.contact_phone = self._parse_phone(entity_text)
                elif 'NAME' in entity_type:
                    result.contact_name = entity_text

                confidences.append(confidence)
                result.entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    text=entity_text,
                    value=entity_text,
                    confidence=confidence,
                    start=entity.get('start', 0),
                    end=entity.get('end', 0)
                ))

            result.model_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return result

        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return self._fallback_extract(text)

    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price from entity text."""
        from ..scrapers.base import BaseScraper
        return BaseScraper.clean_price_text(text)

    def _parse_area(self, text: str) -> Optional[float]:
        """Parse area from entity text."""
        from ..scrapers.base import BaseScraper
        return BaseScraper.clean_area_text(text)

    def _parse_number(self, text: str) -> Optional[int]:
        """Parse integer from text."""
        import re
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None

    def _parse_phone(self, text: str) -> Optional[str]:
        """Parse phone number."""
        from ..scrapers.base import BaseScraper
        return BaseScraper.extract_phone(text)

    def _normalize_legal_status(self, text: str) -> Optional[str]:
        """Normalize legal status."""
        text_lower = text.lower()
        for key, value in self.LEGAL_STATUS_MAP.items():
            if key in text_lower:
                return value
        return text

    def _normalize_property_type(self, text: str) -> Optional[str]:
        """Normalize property type."""
        text_lower = text.lower()
        for key, value in self.PROPERTY_TYPE_MAP.items():
            if key in text_lower:
                return value
        return text

    def _fallback_extract(self, text: str) -> NERResult:
        """Fallback rule-based extraction."""
        from .fallback import FallbackExtractor
        fallback = FallbackExtractor()
        return fallback.extract(text)

    def batch_extract(self, texts: List[str]) -> List[NERResult]:
        """Extract entities from multiple texts."""
        return [self.extract_entities(text) for text in texts]

    def train(self, train_dataset, val_dataset, output_dir: str, num_epochs: int = 3):
        """Fine-tune PhoBERT on custom NER dataset."""
        from transformers import Trainer, TrainingArguments, DataCollatorForTokenClassification
        from datasets import Dataset

        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f"{output_dir}/logs",
            logging_steps=100,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True
        )

        # Data collator
        data_collator = DataCollatorForTokenClassification(
            tokenizer=self.tokenizer
        )

        # Compute metrics
        def compute_metrics(pred):
            from seqeval.metrics import accuracy_score, f1_score, precision_score, recall_score

            predictions, labels = pred
            predictions = predictions.argmax(axis=-1)

            # Convert to list of tags
            true_predictions = [
                [self.model.config.id2label[p] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [self.model.config.id2label[l] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]

            return {
                "accuracy": accuracy_score(true_labels, true_predictions),
                "f1": f1_score(true_labels, true_predictions),
                "precision": precision_score(true_labels, true_predictions),
                "recall": recall_score(true_labels, true_predictions)
            }

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
            compute_metrics=compute_metrics
        )

        trainer.train()
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        logger.info(f"Model saved to {output_dir}")

    def __enter__(self):
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
