import asyncio
import time
from loguru import logger
import random
import json

from pipecat.frames.frames import TextFrame, TTSSpeakFrame, ErrorFrame
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from openai.types.chat import ChatCompletionMessageParam
from nvidia_pipecat.utils.tracing import traceable, AttachmentStrategy, traced
from .nvidia_aiq import NvidiaAIQService

@traceable
class TokkioNvidiaAIQService(NvidiaAIQService):
    def __init__(
        self,
        filler: list[str],
        time_delay: float = 1.0,
        aiq_server_url: str = "http://localhost:8000",
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 200,
        use_knowledge_base: bool = True,
        **kwargs
    ):
        """Initialize"""
        self.filler = filler
        self.time_delay = time_delay
        self.timeout = 120 # Request timeout value. If no chunks are received within this time duration, the endpoint is considered to be unreachable.
        
        # Pass all AIQ-specific parameters to parent
        super().__init__(
            aiq_server_url=aiq_server_url,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_knowledge_base=use_knowledge_base,
            **kwargs
        )

    @traced(attachment_strategy=AttachmentStrategy.NONE, name="aiq")
    async def _get_aiq_response(self, request_json: dict):
        resp = await self.shared_session.post(f"{self.aiq_server_url}/chat/stream", json=request_json)
        return resp
    
    async def _process_context(self, context: OpenAILLMContext):
        try:
            messages: list[ChatCompletionMessageParam] = context.get_messages()
            chat_details = []

            for msg in messages:
                if msg["role"] != "system" and msg["role"] != "user" and msg["role"] != "assistant":
                    raise Exception(f"Unexpected role {msg['role']} found!")
                chat_details.append({"role": msg["role"], "content": msg["content"]})

            logger.debug(f"Chat details: {chat_details}")

            if len(chat_details) == 0 or all(msg["content"] == "" for msg in chat_details):
                raise Exception("No query name is provided..")

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
            
            start_time = time.time()
            first_chunk_received = False
            full_response = ""
            
            # Create a flag to track if we've already said a filler phrase
            filler_said = False
            
            # Create a task to monitor the request time and trigger filler phrase if needed
            async def monitor_request_time():
                nonlocal filler_said
                await asyncio.sleep(self.time_delay)
                if not first_chunk_received and not filler_said:
                    filler_said = True
                    random_filler = random.choice(self.filler)
                    await self.push_frame(TTSSpeakFrame(random_filler))
            
            # Start the monitoring task
            monitor_task = asyncio.create_task(monitor_request_time())
            resp = await self._get_aiq_response(request_json)
            try:
                chunk = ""
                async for current_chunk, _ in resp.content.iter_chunks():
                    if not first_chunk_received:
                        elapsed_time = time.time() - start_time
                        logger.debug(f"Elapsed time: {elapsed_time}")
                        logger.debug(f"Time delay: {self.time_delay}")
                        first_chunk_received = True
                        
                        # Cancel the monitoring task since we've received a response
                        if not monitor_task.done():
                            monitor_task.cancel()
                            try:
                                await monitor_task
                            except asyncio.CancelledError:
                                pass

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
                            # aggregated version of the chunk from AIQ or erroneous chunk is received from AIQ
                            logger.debug(f"Parsing AIQ response chunk failed. Error: {e}")
                            message = ""
                        if not message:
                            continue
                        full_response += message
                        if message:
                            await self.push_frame(TextFrame(message))
                    except Exception as e:
                        await self.push_error(ErrorFrame("Internal error in AIQ stream: " + str(e)))
            finally:
                resp.close()
            logger.debug(f"Full AIQ response: {full_response}")

        except Exception as e:
            logger.error(f"An error occurred in http request to AIQ endpoint, Error:  {e}")
            await self.push_frame(TTSSpeakFrame("Cannot connect to the AIQ endpoint"))
            return
