# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)

"""
MCP Client Module
Handles communication with Model Context Protocol
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import requests

from config.settings import Settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP services."""
    
    DEFAULT_TIMEOUT = 300  # Increased to 90 seconds to handle complex requests and reduce Read timeout errors
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or Settings.MCP_API_KEY
        self.endpoint = endpoint or Settings.MCP_ENDPOINT
        self.model = model or getattr(Settings, "MCP_MODEL", None)
        self.timeout = timeout
        self.session: Optional[requests.Session] = None
        self.last_response: Optional[Dict[str, Any]] = None
        self.last_request: Optional[Dict[str, Any]] = None
        self.last_token_usage: Optional[Dict[str, Any]] = None
    
    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    
    def connect(self) -> None:
        """Establish connection to MCP/LLM service."""
        if not self.api_key:
            raise ValueError("MCP API key is not configured.")
        if not self.endpoint:
            raise ValueError("MCP endpoint is not configured.")
        
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
            logger.debug("MCP client session initialized.")
    
    def disconnect(self) -> None:
        """Close connection to MCP service."""
        if self.session is not None:
            self.session.close()
            self.session = None
            logger.debug("MCP client session closed.")
    
    # ------------------------------------------------------------------ #
    # Request / response handling
    # ------------------------------------------------------------------ #
    
    def send_request(
        self,
        prompt: str,
        context: Optional[str] = None,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
        initial_backoff: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Send request to MCP service with retry logic for rate limits.
        
        Args:
            prompt: User prompt for the LLM.
            context: Optional system or architectural context.
            temperature: Sampling temperature.
            max_tokens: Optional completion token limit.
            extra_params: Additional parameters forwarded to the API.
            max_retries: Maximum number of retry attempts for 429 errors.
            initial_backoff: Initial backoff delay in seconds (doubles each retry).
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        
        if self.session is None:
            self.connect()
        
        # Check if using Google Gemini API
        is_gemini = "generativelanguage.googleapis.com" in self.endpoint
        
        # Prepare payload once
        if is_gemini:
            endpoint_with_key = f"{self.endpoint}?key={self.api_key}"
            payload = self._build_gemini_payload(
                prompt=prompt,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            headers = {"Content-Type": "application/json"}
        else:
            endpoint_with_key = self.endpoint
            payload = self._build_payload(
                prompt=prompt,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_params=extra_params,
            )
            headers = None
        
        self.last_request = payload
        
        # Retry loop with exponential backoff
        backoff_delay = initial_backoff
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Make the request
                if is_gemini:
                    response = requests.post(
                        endpoint_with_key,
                        data=json.dumps(payload),
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    response = self.session.post(
                        endpoint_with_key,
                        data=json.dumps(payload),
                        timeout=self.timeout,
                    )
                
                # Check for rate limit error (429)
                if response.status_code == 429:
                    if attempt < max_retries:
                        logger.warning(
                            f"Rate limit (429) encountered. Retrying in {backoff_delay:.1f}s "
                            f"(attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(backoff_delay)
                        backoff_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Final attempt failed
                        logger.error(f"Rate limit (429) persisted after {max_retries} retries.")
                        response.raise_for_status()
                
                # Check for other errors
                response.raise_for_status()
                
                # Success - parse response
                data = response.json()
                self.last_response = data
                
                # Extract token usage based on provider
                if is_gemini:
                    usage_meta = data.get("usageMetadata", {})
                    self.last_token_usage = {
                        "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                        "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                        "total_tokens": usage_meta.get("totalTokenCount", 0),
                    }
                else:
                    self.last_token_usage = data.get("usage")
                
                if attempt > 0:
                    logger.info(f"Request succeeded after {attempt + 1} attempts.")
                else:
                    logger.debug("MCP request completed successfully.")
                
                return data
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429 and attempt < max_retries:
                    # Already handled above, but catch here for safety
                    logger.warning(
                        f"Rate limit (429) caught in exception handler. Retrying in {backoff_delay:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                else:
                    # Re-raise if not 429 or out of retries
                    raise
            
            except requests.exceptions.Timeout as e:
                # Timeout errors - retry with backoff
                last_exception = e
                if attempt < max_retries:
                    logger.warning(
                        f"Request timed out after {self.timeout}s. Retrying in {backoff_delay:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                else:
                    logger.error(f"Request timed out after {max_retries} retry attempts.")
                    raise
            
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                # Non-retryable errors
                logger.error(f"Request failed with non-retryable error: {e}")
                raise
        
        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed after all retry attempts.")
    
    def receive_response(self) -> Optional[Dict[str, Any]]:
        """Return the last response object."""
        return self.last_response
    
    def get_token_usage(self) -> Optional[Dict[str, Any]]:
        """Get token usage for the last request."""
        return self.last_token_usage or {}
    
    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    
    def _build_payload(
        self,
        *,
        prompt: str,
        context: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        extra_params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Construct payload compatible with OpenAI style APIs."""
        system_prompt = (
            context
            or "You are an MCP-enabled software engineering assistant that returns JSON-friendly responses."
        )
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        
        if extra_params:
            payload.update(extra_params)
        
        # If the endpoint expects a non-chat payload, allow overriding via extra_params
        if payload.get("model") is None:
            payload.pop("model", None)
        
        return payload
    
    def _build_gemini_payload(
        self,
        *,
        prompt: str,
        context: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        """Construct payload for Google Gemini API."""
        # Combine context and prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            }
        }
        
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        
        return payload
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """Extract text from API response, handling both OpenAI and Gemini formats."""
        # Check if Gemini format
        if "candidates" in response:
            # Gemini format
            try:
                return response["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.warning(f"Failed to extract text from Gemini response: {e}")
                return str(response)
        
        # OpenAI format
        elif "choices" in response:
            try:
                return response["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                logger.warning(f"Failed to extract text from OpenAI response: {e}")
                return str(response)
        
        # Unknown format, return as string
        return str(response)
