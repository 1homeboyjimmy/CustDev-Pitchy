import httpx
import json
from typing import Any, Dict, Optional
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('pitchy.rag_service')

class RagService:
    """
    RAG Service to fetch real-world market context from the main server.
    """
    
    @staticmethod
    async def get_market_context(startup_description: str) -> str:
        """
        Fetch market context from the external RAG service based on the startup description.
        
        Args:
            startup_description: A brief description of the startup/project.
            
        Returns:
            str: The retrieved market context or an empty string if failed.
        """
        if not Config.MAIN_SERVER_RAG_URL:
            logger.warning("MAIN_SERVER_RAG_URL not configured, skipping external RAG context lookup")
            return ""
            
        logger.info(f"Fetching market context from external RAG: {Config.MAIN_SERVER_RAG_URL}")
        
        headers = {
            "Content-Type": "application/json"
        }
        if Config.RAG_API_KEY:
            headers["Authorization"] = f"Bearer {Config.RAG_API_KEY}"
            
        try:
            # Note: We use a POST request with the startup description as the query
            payload = {
                "query": startup_description
            }
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    Config.MAIN_SERVER_RAG_URL,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"RAG service returned error {response.status_code}: {response.text}")
                    return ""
                    
                data = response.json()
                
                # The expected response structure might vary, we try common fields
                # but focus on getting any relevant string data.
                context = ""
                if isinstance(data, dict):
                    # Try explicit fields
                    context = data.get("context") or data.get("result") or data.get("answer")
                    if not context and "data" in data:
                        context = data["data"].get("context") or data["data"].get("result")
                
                if not context:
                    # If we can't find a specific field, use the first string value or the whole object
                    if isinstance(data, str):
                        context = data
                    else:
                        logger.warning("Could not find explicit 'context' field in RAG response, using raw JSON")
                        context = json.dumps(data, ensure_ascii=False)
                
                logger.info("Successfully retrieved market context from RAG service")
                return context
                
        except httpx.ConnectError:
            logger.error("Could not connect to external RAG service (Connection Error)")
            return ""
        except httpx.TimeoutException:
            logger.error("RAG service request timed out")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error fetching RAG context: {str(e)}")
            return ""
