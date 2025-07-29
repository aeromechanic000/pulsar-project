
import os, aiohttp
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod
from urllib.parse import quote, urljoin

from utils import *

def get_provider(provider_name = "Pollinations") : 
    cls = None
    if provider_name == "Pollinations" :
        cls = PollinationsProvider
    elif provider_name == "Ollama" :
        cls = OllamaProvider
    elif provider_name == "OpenAI" :
        cls = OpenAIProvider
    elif provider_name == "Anthropic" :
        cls = AnthropicProvider
    elif provider_name == "Gemini" :
        cls = GeminiProvider
    elif provider_name in ["Open", "Doubao", "Qwen", "OpenRouter", ] :
        cls = OpenProvider
    return cls

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, prompt: str) -> str :
        """Generate a response from the LLM"""
        return ""
    
class PollinationsProvider(LLMProvider):
    """Pollinations AI provider implementation"""
    
    def __init__(self, config = None):
        self.config = config
        self.base_url = "https://text.pollinations.ai"
    
    async def generate_response(self, prompt : str) -> str :
        """Generate response using Pollinations AI"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{quote(prompt)}"
            async with session.get(url) as response:
                text_response = await response.text()
                return text_response

class OllamaProvider(LLMProvider):
    """Implementation for Provider with OpenAI compatible API"""
    
    def __init__(self, config = None):
        self.config = config
        self.base_url = self.config.get("base_url", "http://127.0.0.1:11434") 
        self.model = self.config.get("model", "llama3.2") 

    async def generate_response(self, prompt : str) -> str :
        """Generate response using Pollinations AI"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
            }

            payload = {
                "model" : self.model, 
                "prompt" : prompt, 
                "stream" : False,
            }

            async with session.post(urljoin(self.base_url, "api/generate"), headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return  response_data.get("response", "")
                else :
                    add_log(f"Invalid provider response: {response}", "error")

class OpenProvider(LLMProvider):
    """Implementation for Provider with OpenAI compatible API"""
    
    def __init__(self, config = None):
        self.config = config
        self.base_url = self.config.get("base_url", "") 
        self.model = self.config.get("model", "") 
        self.api_key = self.config.get("api_key", "") 
        self.env_name = self.config.get("env_name", "") 

        if len(self.api_key.strip()) < 1 and len(self.env_name.strip()) > 0 : 
            self.api_key = os.environ.get(self.env_name)
    
    async def generate_response(self, prompt : str) -> str :
        """Generate response using OpenAI compatible provider"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model" : self.model, 
                "messages" : [{"role" : "user", "content" : prompt}],  
                "stream" : False,
            }

            async with session.post(urljoin(self.base_url, "chat/completions"), headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if "choices" in response_data:
                        message_content = response_data["choices"][0]["message"].get("content")
                        reasoning_content = response_data["choices"][0]["message"].get("reasoning_content")

                        if message_content is not None:
                            return message_content
                        elif reasoning_content is not None:
                            return reasoning_content
                else :
                    add_log(f"Invalid provider response: {response}", "error")

class OpenAIProvider(LLMProvider):
    """Implementation for OpenAI API"""
    
    def __init__(self, config = None):
        self.config = config
        self.model = self.config.get("model", "") 
        self.api_key = self.config.get("api_key", "") 
        self.base_url = "https://api.openai.com/v1/"
        self.env_name = "OPENAI_API_KEY" 

        if len(self.api_key.strip()) < 1 : 
            self.api_key = os.environ.get(self.env_name)
    
    async def generate_response(self, prompt : str) -> str :
        """Generate response using Anthropic API"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model" : self.model, 
                "input" : prompt,  
                "stream" : False,
            }

            async with session.post(urljoin(self.base_url, "responses"), headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = response.json()
                    if "output" in response_data.keys() : 
                        return response_data["output"][0]["content"][0]["text"]
                else :
                    add_log(f"Invalid provider response: {response}", "error")

class AnthropicProvider(LLMProvider):
    """Implementation for Anthropic API"""
    
    def __init__(self, config = None):
        self.config = config
        self.model = self.config.get("model", "") 
        self.api_key = self.config.get("api_key", "") 
        self.base_url = "https://api.anthropic.com/v1/"
        self.env_name = "ANTHROPIC_API_KEY"

        if len(self.api_key.strip()) < 1 : 
            self.api_key = os.environ.get(self.env_name)
    
    async def generate_response(self, prompt : str) -> str :
        """Generate response using Anthropic API"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": f"{self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model" : self.model, 
                "messages" : [{"role" : "user", "content" : prompt}],  
                "stream" : False,
            }

            async with session.post(urljoin(self.base_url, "messages"), headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data["content"][0]["text"]
                else :
                    add_log(f"Invalid provider response: {response}", "error")

class GeminiProvider(LLMProvider):
    """Implementation for Gemini API"""
    
    def __init__(self, config = None):
        self.config = config
        self.model = self.config.get("model", "") 
        self.api_key = self.config.get("api_key", "") 
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.env_name = "GEMINI_API_KEY"

        if len(self.api_key.strip()) < 1 : 
            self.api_key = os.environ.get(self.env_name)
    
    async def generate_response(self, prompt : str) -> str :
        """Generate response using Gemini API"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
            }

            payload = {
                "contents" : {
                    "parts" : [{"text" : prompt}], 
                },
            }

            url = "%s/models/%s:generateContent?key=%s" % (self.base_url, self.model, self.api_key)

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if "candidates" in response_data.keys() : 
                        return response_data["candidates"][0]["content"]["parts"][0]["text"]
                else :
                    add_log(f"Invalid provider response: {response}", "error")