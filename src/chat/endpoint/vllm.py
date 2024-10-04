import json
from typing import Any, Dict, Union

import httpx
from httpx import ConnectError
from loguru import logger
from pydantic import ValidationError

from .base import (
    StructuredGenerationChatEndPoint,
    StructureGenerationFailure,
    StructureOutputResponse,
)


class VLLMConnectionError(Exception):
    pass


class VLLMStructureGeneration(StructuredGenerationChatEndPoint):
    def __init__(self, chat_config: Dict[str, Any]) -> None:
        logger.trace("CHAT-VLLM chat model initializing")
        self.chat_config = chat_config
        self.header = {"accept": "application/json", "Content-Type": "application/json"}
        self.request_url = chat_config["chat_vllm_endpoint"]
        logger.trace(f"CHAT-VLLM chat model endpoint: {self.request_url}")
        self.chat_model = chat_config["chat_model"]
        logger.trace(f"CHAT-VLLM chat model: {self.chat_model}")
        self.chat_max_new_token = chat_config["chat_max_new_token"]
        logger.trace(f"CHAT-VLLM chat max new token: {self.chat_max_new_token}")
        self.chat_model_type = chat_config["chat_model_type"]
        logger.trace(f"CHAT-VLLM chat model type: {self.chat_model_type}")
        if self.chat_model_type == "completion":
            logger.trace("CHAT-VLLM chat model type is completion")
            self.endpoint_suffix = "/v1/completions"
        else:
            logger.trace("CHAT-VLLM chat model type is chat")
            self.chat_system_message = chat_config["chat_system_message"]
            logger.trace(f"CHAT-VLLM chat system message: {self.chat_system_message}")
            self.endpoint_suffix = "/v1/chat/completions"
        logger.trace(f"CHAT-VLLM chat model endpoint suffix: {self.endpoint_suffix}")
        self.chat_request_timeout = chat_config["chat_request_timeout"]
        logger.trace(f"CHAT-VLLM chat request timeout: {self.chat_request_timeout}")
        self.chat_parameters = chat_config["chat_parameters"]
        logger.trace(f"CHAT-VLLM chat parameters: {self.chat_parameters}")
        # check if vllm is alive otherwise raise an error
        try:
            with httpx.Client(timeout=self.chat_request_timeout) as client:
                response = client.get(url=f"{self.request_url}/health")
            if response.status_code != 200:
                raise VLLMConnectionError("VLLM is not available")
        except ConnectError as e:
            raise VLLMConnectionError(
                f"Failed to connect VLLM from {self.request_url}"
            ) from e

    def __call__(
        self, prompt: str, schema: Any
    ) -> Union[StructureGenerationFailure, StructureOutputResponse]:
        if self.chat_model_type == "completion":
            request_data = {
                **{
                    "model": self.chat_model,
                    "max_tokens": self.chat_max_new_token,
                    "prompt": [f"{prompt}"],
                    "guided_json": json.dumps(schema),
                },
                **self.chat_parameters,
            }
        else:
            request_data = {
                **{
                    "model": self.chat_model,
                    "max_tokens": self.chat_max_new_token,
                    "messages": [
                        {"content": self.chat_system_message, "role": "system"},
                        {"content": prompt, "role": "user"},
                    ],
                    "guided_json": json.dumps(schema),
                },
                **self.chat_parameters,
            }
        with httpx.Client(timeout=self.chat_request_timeout) as client:
            response = client.post(
                url=f"{self.request_url}{self.endpoint_suffix}",
                headers=self.header,
                json=request_data,
            )
        if response.status_code != 200:
            logger.error(f"CHAT-VLLM response status code: {response.status_code}")
            logger.error(f"CHAT-VLLM response text: {response.json()}")
            return StructureGenerationFailure()
        try:
            if self.chat_model_type == "completion":
                response_dict = json.loads(response.json()["choices"][0]["text"])
            else:
                response_dict = json.loads(
                    response.json()["choices"][0]["message"]["content"]
                )
            if "short_memory_ids" in response_dict:
                response_dict["short_memory_ids"] = list(
                    set(response_dict["short_memory_ids"])
                )
            if "mid_memory_ids" in response_dict:
                response_dict["mid_memory_ids"] = list(
                    set(response_dict["mid_memory_ids"])
                )
            if "long_memory_ids" in response_dict:
                response_dict["long_memory_ids"] = list(
                    set(response_dict["long_memory_ids"])
                )
            if "reflection_memory_ids" in response_dict:
                response_dict["reflection_memory_ids"] = list(
                    set(response_dict["reflection_memory_ids"])
                )
            response_pydantic = StructureOutputResponse(**response_dict)
        except json.JSONDecodeError:
            logger.error("CHAT-VLLM json decoder error")
            logger.error(f"CHAT-VLLM response text: {response.json()}")
            return StructureGenerationFailure()
        except ValidationError as e:
            logger.error("CHAT-VLLM pydantic validation error")
            logger.error(f"CHAT-VLLM response text: {response.json()}")
            logger.error(f"CHAT-VLLM pydantic error: {e}")
            return StructureGenerationFailure()

        return response_pydantic
