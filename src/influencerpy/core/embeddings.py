import json
import logging
import hashlib
from typing import List, Optional
from datetime import datetime
from sqlmodel import select
from sentence_transformers import SentenceTransformer, util
from influencerpy.database import get_session
from influencerpy.types.schema import ContentEmbedding
from influencerpy.logger import get_app_logger

logger = get_app_logger("embeddings")

class EmbeddingManager:
    """Manages content embeddings and similarity checks.
    
    For low-memory environments (e.g., e2-micro with 1GB RAM), consider using:
    - "paraphrase-MiniLM-L3-v2" (smallest, ~40MB, fastest)
    - "all-MiniLM-L6-v2" (default, ~80MB, good balance)
    - "Ayeshas21/sentence-transformers-all-MiniLM-L6-v2-quantized" (quantized, ~20MB, slower)
    
    Can be disabled via config: embeddings.enabled = false
    """
    
    _model: Optional[SentenceTransformer] = None
    _enabled: Optional[bool] = None
    
    def __init__(self, model_name: str = None):
        # Check if embeddings are enabled
        try:
            from influencerpy.config import ConfigManager
            config_manager = ConfigManager()
            self._enabled = config_manager.get("embeddings.enabled", True)
        except Exception:
            self._enabled = True  # Default to enabled
        
        if not self._enabled:
            logger.info("Embeddings are disabled via configuration. Only exact hash matching will be used.")
            self.model_name = None  # Don't load model if disabled
            return
        
        # Check config first, then auto-detect, then use default
        if model_name is None:
            try:
                from influencerpy.config import ConfigManager
                config_manager = ConfigManager()
                model_name = config_manager.get("embeddings.model_name")
            except Exception:
                pass  # Config not available, continue with auto-detection
        
        if model_name is None:
            # Auto-select based on available memory for low-memory environments
            try:
                import psutil
                # Use available memory (not total) to better reflect actual constraints
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                
                # Auto-select based on available memory
                if available_memory_gb < 1.5:
                    # Very constrained (e.g., e2-micro): use smallest model
                    self.model_name = "paraphrase-MiniLM-L3-v2"
                    logger.info(f"Low memory detected ({available_memory_gb:.1f}GB available). Using lightweight model: {self.model_name}")
                else:
                    # Default: balanced model
                    self.model_name = "all-MiniLM-L6-v2"
            except ImportError:
                # psutil not available, use default
                self.model_name = "all-MiniLM-L6-v2"
                logger.debug("psutil not available, using default model. Install psutil for automatic model selection.")
            except Exception as e:
                # Fallback on any error
                self.model_name = "all-MiniLM-L6-v2"
                logger.debug(f"Could not detect memory, using default model: {e}")
        else:
            self.model_name = model_name
    
    @property
    def enabled(self) -> bool:
        """Check if embeddings are enabled."""
        if self._enabled is None:
            try:
                from influencerpy.config import ConfigManager
                config_manager = ConfigManager()
                self._enabled = config_manager.get("embeddings.enabled", True)
            except Exception:
                self._enabled = True
        return self._enabled
        
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if not self.enabled:
            raise RuntimeError("Embeddings are disabled. Cannot load model.")
        if self._model is None:
            if not self.model_name:
                raise RuntimeError("Model name not set. Embeddings may be disabled.")
            logger.info(f"Loading embedding model: {self.model_name}")
            # Use CPU-only mode to reduce memory usage (no GPU overhead)
            # This is especially important for low-memory instances
            import os
            os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # Force CPU
            self._model = SentenceTransformer(self.model_name, device='cpu')
            logger.info(f"Model loaded on CPU (memory-efficient mode)")
        return self._model
        
    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of text for exact match check."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
        
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self.model.encode(text, convert_to_tensor=False).tolist()
        
    def is_similar(self, text: str, threshold: float = 0.95) -> bool:
        """
        Check if text is similar to any existing content.
        Returns True if similarity > threshold.
        
        When embeddings are disabled, only checks exact hash matches.
        """
        if not text or not text.strip():
            return False
            
        content_hash = self._compute_hash(text)
        
        # 1. Check exact match via hash (always available, even when embeddings disabled)
        with next(get_session()) as session:
            existing = session.exec(
                select(ContentEmbedding).where(ContentEmbedding.content_hash == content_hash)
            ).first()
            if existing:
                logger.info("Duplicate content found (exact match).")
                return True
        
        # 2. If embeddings disabled, only exact matches are checked
        if not self.enabled:
            return False
                
        # 3. Check semantic similarity (only if embeddings enabled)
        with next(get_session()) as session:
            all_embeddings = session.exec(select(ContentEmbedding)).all()
            
        if not all_embeddings:
            return False
            
        # Convert current text to embedding
        current_embedding = self.model.encode(text, convert_to_tensor=True)
        
        # Check against stored embeddings
        stored_vectors = []
        for item in all_embeddings:
            try:
                vec = json.loads(item.embedding_json)
                stored_vectors.append(vec)
            except Exception:
                continue
                
        if not stored_vectors:
            return False
            
        # Convert stored vectors to tensor on the same device as current_embedding
        import torch
        stored_vectors_tensor = torch.tensor(stored_vectors, device=current_embedding.device)
            
        # Compute cosine similarity
        similarities = util.cos_sim(current_embedding, stored_vectors_tensor)
        max_similarity = similarities.max().item()
        
        if max_similarity > threshold:
            logger.info(f"Duplicate content found (similarity: {max_similarity:.2f}).")
            return True
        else:
            logger.info(f"Content is unique (max similarity: {max_similarity:.2f}).")
            
        return False
        
    def add_item(self, text: str, source_type: str = "retrieved"):
        """Add content embedding to database.
        
        When embeddings are disabled, only stores the hash for exact matching.
        """
        if not text or not text.strip():
            return
        
        if not self.enabled:
            # When disabled, only store hash for exact matching
            try:
                content_hash = self._compute_hash(text)
                item = ContentEmbedding(
                    content_hash=content_hash,
                    embedding_json="null",  # Store null JSON when disabled
                    source_type=source_type
                )
                with next(get_session()) as session:
                    session.add(item)
                    session.commit()
                logger.debug(f"Indexed content hash only ({source_type}) - embeddings disabled.")
            except Exception as e:
                logger.error(f"Failed to index content hash: {e}")
            return
            
        try:
            embedding = self.get_embedding(text)
            content_hash = self._compute_hash(text)
            
            item = ContentEmbedding(
                content_hash=content_hash,
                embedding_json=json.dumps(embedding),
                source_type=source_type
            )
            
            with next(get_session()) as session:
                session.add(item)
                session.commit()
                
            logger.info(f"Indexed content embedding ({source_type}).")
        except Exception as e:
            logger.error(f"Failed to index content: {e}")
