
"""NVIDIA AIQ service implementation."""

import json

import aiohttp
from loguru import logger
from openai.types.chat import ChatCompletionMessageParam
from pipecat.frames.frames import ErrorFrame, Frame, TextFrame, DataFrame, ServiceUpdateSettingsFrame
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.openai import OpenAILLMService


class NvidiaAIQService(OpenAILLMService):

    _shared_session: aiohttp.ClientSession | None = None

    def __init__(
        self,
        aiq_server_url: str = "http://localhost:8000",
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 200,
        use_knowledge_base: bool = True,
        session: aiohttp.ClientSession | None = None,
        **kwargs
    ):
        super().__init__(api_key="", **kwargs)
        self.aiq_server_url = aiq_server_url
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.use_knowledge_base = use_knowledge_base
        self._external_client_session = None

        if session is not None:
            self._external_client_session = session

    @property
    def shared_session(self) -> aiohttp.ClientSession:
        """Get the shared HTTP client session.

        Returns:
            aiohttp.ClientSession: The shared session for making HTTP requests.
            Creates a new session if none exists and no external session was provided.
        """
        if self._external_client_session is not None:
            return self._external_client_session

        if NvidiaAIQService._shared_session is None:
            NvidiaAIQService._shared_session = aiohttp.ClientSession()
        return NvidiaAIQService._shared_session

    @shared_session.setter
    def shared_session(self, shared_session: aiohttp.ClientSession):
        """Set the shared HTTP client session.

        Args:
            shared_session: The aiohttp ClientSession to use for all instances.
        """
        NvidiaAIQService._shared_session = shared_session

    async def cleanup(self):
        """Clean up resources used by the AIQ service.

        Closes the shared HTTP client session if it exists and performs parent cleanup.
        """
        await super().cleanup()
        await self._close_client_session()

    async def _close_client_session(self):
        """Close the Client Session if it exists."""
        if NvidiaAIQService._shared_session:
            await NvidiaAIQService._shared_session.close()
            NvidiaAIQService._shared_session = None

    async def _process_context(self, context: OpenAILLMContext):
        """Processes LLM context through AIQ pipeline.

        Args:
            context: Contains conversation history and settings.

        Raises:
            Exception: If invalid message role or empty query.
        """
        try:
            messages: list[ChatCompletionMessageParam] = context.get_messages()
            chat_details = []

            for msg in messages:
                if msg["role"] != "system" and msg["role"] != "user" and msg["role"] != "assistant":
                    raise Exception(f"Unexpected role {msg['role']} found!")
                chat_details.append({"role": msg["role"], "content": msg["content"]})

            logger.debug(f"Chat details: {chat_details}")

            if len(chat_details) == 0 or all(msg["content"] == "" for msg in chat_details):
                raise Exception("No query is provided..")

            """
            Call the AIQ server and return the streaming response.
            """
            request_json = {
                "messages": chat_details,
                "use_knowledge_base": self.use_knowledge_base,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens
            }

            await self.start_ttfb_metrics()

            full_response = ""
            async with self.shared_session.post(f"{self.aiq_server_url}/chat/stream", json=request_json) as resp:
                chunk = ""
                async for current_chunk, _ in resp.content.iter_chunks():
                    if not current_chunk:
                        continue

                    await self.stop_ttfb_metrics()

                    try:
                        current_chunk = current_chunk.decode("utf-8")
                        current_chunk = current_chunk.strip("\n")

                        # When citations are returned in the response, the chunks are getting truncated.
                        # Hence, aggregating them below.
                        if current_chunk.startswith("data: "):
                            chunk = current_chunk
                        else:
                            chunk += current_chunk

                        try:
                            if len(chunk) > 6:
                                parsed = json.loads(chunk[6:])
                                message = parsed["choices"][0]["message"]["content"]
                            else:
                                logger.warning(f"Received empty AIQ response chunk '{chunk}'.")
                                message = ""

                        except Exception as e:
                            # If json parsing of chunk is getting failed, it means we still don't have the final
                            # aggregated version of the chunk from RAG or erroneous chunk is received from RAG
                            logger.debug(f"Parsing AIQ response chunk failed. Error: {e}")
                            message = ""
                        if not message:
                            continue
                        full_response += message
                        if message:
                            await self.push_frame(TextFrame(message))
                    except Exception as e:
                        await self.push_error(ErrorFrame("Internal error in AIQ stream: " + str(e)))

            logger.debug(f"Full AIQ response: {full_response}")

        except Exception as e:
            logger.error(f"An error occurred in http request to AIQ endpoint, Error:  {e}")
            await self.push_error(ErrorFrame("An error occurred in http request to AIQ endpoint, Error: " + str(e)))

    async def _update_settings(self, settings):
        """Updates service settings.

        Args:
            settings: Dictionary of setting name-value pairs.
        """
        for setting, value in settings.items():
            logger.debug(f"Updating {setting} to {value} via ServiceUpdateSettingsFrame ")
            match setting:
                case "aiq_server_url":
                    self.aiq_server_url = value
                case "temperature":
                    self.temperature = value
                case "top_p":
                    self.top_p = value
                case "max_tokens":
                    self.max_tokens = value
                case "use_knowledge_base":
                    self.use_knowledge_base = value
                case _:
                    logger.warning(f"Unknown setting for NvidiaAIQ service: {setting}")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Processes pipeline frames.

        Handles settings updates and parent frame processing.

        Args:
            frame: Input frame to process.
            direction: Frame processing direction.
        """
        if isinstance(frame, ServiceUpdateSettingsFrame):
            await self._update_settings(frame.settings)

        await super().process_frame(frame, direction)