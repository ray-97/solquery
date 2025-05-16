from typing import Dict, Any, Optional
from . import data_sources
from . import llm_service # This is your Gemini LLM service
from ..schemas.common_schemas import SentimentAnalysisResult

class SentimentService:
    async def get_sentiment_for_target(
        self, 
        target_identifier: str, # collection name or token symbol/mint
        target_type: str, # "nft_collection" or "token"
    ) -> SentimentAnalysisResult:
        """
        Orchestrates fetching text for a target and then getting its sentiment.
        """
        text_data_result: Dict[str, Any]
        if target_type == "nft_collection":
            text_data_result = await data_sources.get_text_for_sentiment_service(nft_collection_name=target_identifier)
        elif target_type == "token":
            text_data_result = await data_sources.get_text_for_sentiment_service(token_identifier=target_identifier)
        else:
            return SentimentAnalysisResult(
                target_name=target_identifier, target_type=target_type,
                sentiment_data={"error": "Invalid target_type for sentiment analysis."},
                source_text_preview=None
            )

        if text_data_result.get("error"):
            return SentimentAnalysisResult(
                target_name=target_identifier, target_type=target_type,
                sentiment_data={"error": f"Could not fetch text for {target_identifier}: {text_data_result['error']}"}
            )

        text_to_analyze = text_data_result.get("text")
        topic = text_data_result.get("topic", target_identifier)

        if not text_to_analyze:
            return SentimentAnalysisResult(
                target_name=target_identifier, target_type=target_type,
                sentiment_data={"error": f"No text found to analyze for {target_identifier}."}
            )

        # Call the existing sentiment analysis function in llm_service.py
        sentiment_llm_result = await llm_service.analyze_sentiment_with_llm(text_to_analyze, topic=topic)

        if sentiment_llm_result.get("error"):
            return SentimentAnalysisResult(
                target_name=target_identifier, target_type=target_type,
                sentiment_data={"error": f"Sentiment analysis failed: {sentiment_llm_result.get('raw_response', sentiment_llm_result['error'])}"}
            )
        
        return SentimentAnalysisResult(
            target_name=target_identifier,
            target_type=target_type,
            sentiment_data=sentiment_llm_result, # Expected: {"sentiment_classification": ..., "justification": ...}
            source_text_preview=text_to_analyze[:250] + "..." if text_to_analyze else None
        )

sentiment_service_instance = SentimentService()