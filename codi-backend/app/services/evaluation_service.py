"""Evaluation service for assessing AI output quality using Gemini."""
import logging
import json
from typing import Dict, List
from uuid import UUID

from opik import track
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.opik_service import get_opik_service
from app.models.trace import Trace, Evaluation

logger = logging.getLogger(__name__)


class EvaluationService:
    """Automated evaluation of AI outputs using Gemini as judge."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.opik_service = get_opik_service()
    
    @track
    async def evaluate_code_quality(
        self,
        code: str,
        user_opik_enabled: bool,
        model: str = settings.gemini_model
    ) -> Dict:
        """
        Evaluate generated code quality using Gemini.
        
        Returns dict with score (0-1), reason, and metadata.
        """
        gemini_client = self.opik_service.get_gemini_client(user_opik_enabled)
        
        prompt = f"""
Rate the following code on a scale of 0-1 based on:
- Readability (clear variable names, good structure)
- Best practices (proper error handling, efficient algorithms)
- Maintainability (comments where needed, modular design)

Code:
```
{code}
```

Respond with JSON in this exact format:
{{"score": 0.85, "reason": "Clear structure with good variable names. Could improve error handling."}}

Only return the JSON, nothing else.
"""
        
        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        try:
            # Extract JSON from response
            result_text = response.text.strip()
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            return {
                "score": float(result.get("score", 0.5)),
                "reason": result.get("reason", ""),
                "meta_data": {"model": model}
            }
        except Exception as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
            return {
                "score": 0.5,
                "reason": "Failed to evaluate",
                "meta_data": {"error": str(e)}
            }
    
    @track
    async def evaluate_summary_quality(
        self,
        summary: str,
        instruction: str,
        user_opik_enabled: bool,
        model: str = settings.gemini_model
    ) -> Dict:
        """
        Evaluate summary quality using Gemini.
        
        Returns dict with score (0-1), reason, and metadata.
        """
        gemini_client = self.opik_service.get_gemini_client(user_opik_enabled)
        
        prompt = f"""
Rate this summary on a scale of 0-1 based on:
- Conciseness (no fluff, every word counts)
- Technical accuracy (correct terminology, clear concepts)
- Alignment with instruction: "{instruction}" (directly addresses the request)
- Information density (packed with relevant details)

Summary:
{summary}

Respond with JSON in this exact format:
{{"score": 0.92, "reason": "Highly concise with technical accuracy. Directly addresses the instruction."}}

Only return the JSON, nothing else.
"""
        
        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        try:
            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            return {
                "score": float(result.get("score", 0.5)),
                "reason": result.get("reason", ""),
                "meta_data": {"model": model}
            }
        except Exception as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
            return {
                "score": 0.5,
                "reason": "Failed to evaluate",
                "meta_data": {"error": str(e)}
            }
    
    async def save_evaluation(
        self,
        trace_id: str,
        metric_name: str,
        score: float,
        reason: str,
        meta_data: Dict
    ) -> Evaluation:
        """Save evaluation to database."""
        from uuid import uuid4
        
        evaluation = Evaluation(
            id=str(uuid4()),
            trace_id=trace_id,
            metric_name=metric_name,
            score=score,
            reason=reason,
            meta_data=meta_data
        )
        
        self.db.add(evaluation)
        await self.db.commit()
        await self.db.refresh(evaluation)
        
        logger.info(f"Saved evaluation: {metric_name}={score:.2f} for trace {trace_id}")
        return evaluation
