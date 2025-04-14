# app/core/processing_pipeline/stream_processor.py
import asyncio
import base64
from typing import Dict, Any, Callable, Coroutine, AsyncGenerator, Optional # Added Optional

from app.core.service_registry import service_registry # Use the singleton instance
from app.services.asr.base import BaseASRService
from app.services.llm.base import BaseLLMService
from app.services.tts.base import BaseTTSService

# Define callback types for better type hinting
TranscriptionCallback = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]
LLMCallback = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]
TTSCallback = Callable[[bytes], Coroutine[Any, Any, None]]
ErrorCallback = Callable[[str, Optional[str]], Coroutine[Any, Any, None]] # detail, event_type

class AudioStreamProcessor:
    """Processes an audio stream through ASR, LLM, and TTS pipeline."""

    def __init__(
        self,
        on_transcription: TranscriptionCallback,
        on_llm_response: LLMCallback,
        on_tts_audio: TTSCallback,
        on_error: ErrorCallback,
        session_id: str, # Pass session ID for context if needed by LLM
        user_id: str, # Pass user ID for context/logging
    ):
        self.on_transcription = on_transcription
        self.on_llm_response = on_llm_response
        self.on_tts_audio = on_tts_audio
        self.on_error = on_error
        self.session_id = session_id
        self.user_id = user_id

        # Get services from registry
        self.asr_service: Optional[BaseASRService] = service_registry.get_asr_service()
        self.llm_service: Optional[BaseLLMService] = service_registry.get_llm_service()
        self.tts_service: Optional[BaseTTSService] = service_registry.get_tts_service()

        self._audio_queue = asyncio.Queue[Optional[bytes]]() # Queue for incoming audio chunks
        self._processing_task: Optional[asyncio.Task] = None # Type hint for task
        self._is_receiving_audio = False
        self._full_transcript = ""

    async def _asr_task(self) -> Optional[str]:
        """Task to handle ASR processing."""
        if not self.asr_service:
            await self.on_error("ASR service not available.", "asr_error")
            return None

        final_transcript = None
        try:
            async def audio_generator() -> AsyncGenerator[bytes, None]:
                while True:
                    chunk = await self._audio_queue.get()
                    if chunk is None: # End of stream signal
                        self._audio_queue.task_done() # Mark None as done too
                        break
                    yield chunk
                    self._audio_queue.task_done()

            print("ASR Task: Starting transcription stream...")
            transcription_stream = self.asr_service.transcribe_stream(audio_generator())

            async for result in transcription_stream:
                print(f"ASR Task: Received transcription result: {result}")
                await self.on_transcription(result) # Send intermediate/final results
                if result.get("is_final"):
                    final_transcript = result.get("text")
            print(f"ASR Task: Finished. Final transcript: '{final_transcript}'")
            # Ensure the generator loop fully completes even if no final result emitted
            # This helps release the queue
            
        except Exception as e:
            print(f"ASR Error: {e}")
            await self.on_error(f"ASR processing failed: {e}", "asr_error")
            final_transcript = None # Ensure it's None on error
        finally:
             # If an error occurred, ensure the audio generator loop is unblocked
             if self._is_receiving_audio: 
                 if not self._audio_queue.empty():
                     # Signal generator to stop if it hasn't received None yet
                     try:
                         self._audio_queue.put_nowait(None) 
                     except asyncio.QueueFull:
                         pass 
                         
             # Wait for any remaining items (including None) to be processed by generator
             # This might not be strictly necessary if exception handling is robust
             # await self._audio_queue.join() 
             return final_transcript

    async def _llm_task(self, text: str) -> Optional[str]:
        """Task to handle LLM processing."""
        if not self.llm_service:
            await self.on_error("LLM service not available.", "llm_error")
            return None
        if not text:
            print("LLM Task: No input text, skipping LLM.")
            return None

        llm_full_response = ""
        try:
            print(f"LLM Task: Sending text to LLM: '{text[:100]}...'")
            llm_stream = self.llm_service.generate_response_stream(
                prompt=text,
                # context={"session_id": self.session_id, "user_id": self.user_id}
            )
            async for chunk_dict in llm_stream:
                 print(f"LLM Task: Received chunk: {chunk_dict}")
                 await self.on_llm_response(chunk_dict)
                 llm_full_response += chunk_dict.get("text", "")
                 # No break needed if LLM stream naturally ends
            print(f"LLM Task: Finished. Full response: '{llm_full_response}'")
            return llm_full_response
        except Exception as e:
            print(f"LLM Error: {e}")
            await self.on_error(f"LLM processing failed: {e}", "llm_error")
            return None

    async def _tts_task(self, text: str) -> None:
        """Task to handle TTS processing."""
        if not self.tts_service:
            await self.on_error("TTS service not available.", "tts_error")
            return
        if not text:
             print("TTS Task: No input text, skipping TTS.")
             return

        try:
            print(f"TTS Task: Sending text to TTS: '{text[:100]}...'")
            audio_stream = self.tts_service.synthesize_stream(text)
            async for audio_chunk in audio_stream:
                await self.on_tts_audio(audio_chunk)
            print("TTS Task: Finished sending audio.")
        except Exception as e:
            print(f"TTS Error: {e}")
            await self.on_error(f"TTS processing failed: {e}", "tts_error")

    async def _run_pipeline(self):
        """Runs the ASR -> LLM -> TTS pipeline."""
        print("Pipeline: Starting ASR task...")
        final_transcript = await self._asr_task()

        if final_transcript:
            print("Pipeline: Starting LLM task...")
            llm_response = await self._llm_task(final_transcript)
            if llm_response:
                print("Pipeline: Starting TTS task...")
                await self._tts_task(llm_response)
            else:
                 print("Pipeline: LLM did not return a response, skipping TTS.")
        else:
             print("Pipeline: ASR did not return a final transcript, skipping LLM and TTS.")
        print("Pipeline: Processing finished.")


    async def process_audio_chunk(self, audio_chunk: bytes):
        """Adds an audio chunk to the processing queue."""
        if not self._is_receiving_audio:
            print("Warning: Received audio chunk but not actively receiving.")
            return
        if self._processing_task is None:
            print("Error: Cannot process audio chunk, pipeline not started.")
            await self.on_error("Pipeline not started.", "internal_error")
            return
        await self._audio_queue.put(audio_chunk)

    async def start_processing(self):
        """Starts the audio processing pipeline in the background."""
        if self._processing_task is not None and not self._processing_task.done():
            print("Warning: Processing task already running.")
            # Optionally, cancel the existing task or raise an error
            # self._processing_task.cancel()
            # await asyncio.sleep(0) # Allow cancellation to propagate
            return

        if not self.asr_service or not self.llm_service or not self.tts_service:
             await self.on_error("One or more required services (ASR, LLM, TTS) are not available.", "config_error")
             return

        print("Starting audio processing pipeline...")
        self._is_receiving_audio = True
        self._full_transcript = ""
        # Clear the queue before starting
        while not self._audio_queue.empty():
             try:
                 self._audio_queue.get_nowait()
                 self._audio_queue.task_done()
             except asyncio.QueueEmpty:
                 break
        self._processing_task = asyncio.create_task(self._run_pipeline())

    async def stop_processing(self):
        """Signals the end of audio input and waits for processing to complete."""
        if not self._is_receiving_audio and (self._processing_task is None or self._processing_task.done()):
             print("Warning: Stop called but not actively receiving or processing.")
             return
             
        print("Signaling end of audio stream...")
        self._is_receiving_audio = False
        # Put None only if the task is still running
        if self._processing_task and not self._processing_task.done():
            try:
                self._audio_queue.put_nowait(None) # Signal end to ASR generator
            except asyncio.QueueFull:
                # If queue is full, task is likely blocked; None might not be needed
                # Or potentially cancel the task if it's stuck
                print("Warning: Audio queue full when trying to signal stop.")
                pass 
        else:
            print("Processing task already finished or not started, no stop signal sent to queue.")

        if self._processing_task:
            print("Waiting for pipeline to finish...")
            try:
                # Use a timeout to avoid waiting indefinitely
                await asyncio.wait_for(self._processing_task, timeout=10.0) 
                print("Pipeline finished gracefully.")
            except asyncio.TimeoutError:
                print("Warning: Pipeline task timed out during stop.")
                self._processing_task.cancel()
            except asyncio.CancelledError:
                 print("Pipeline task was cancelled during stop.")
            except Exception as e:
                 print(f"Pipeline task finished with error during stop: {e}")
                 import traceback
                 traceback.print_exc()
            finally:
                 self._processing_task = None # Reset task
        else:
             print("No active processing task to wait for.")


    async def process_text_input(self, text: str):
         """Processes direct text input (skips ASR)."""
         if self._processing_task is not None and not self._processing_task.done():
             print("Warning: Cannot process text input while audio pipeline is running.")
             await self.on_error("Processing audio, please wait.", "busy_error")
             return

         if not self.llm_service or not self.tts_service:
             await self.on_error("Required services (LLM, TTS) are not available for text input.", "config_error")
             return

         print("Pipeline: Starting text processing (LLM -> TTS)...")
         # Run LLM -> TTS in a separate task to avoid blocking WebSocket handler
         async def text_pipeline():
            llm_response = await self._llm_task(text)
            if llm_response:
                await self._tts_task(llm_response)
         
         self._processing_task = asyncio.create_task(text_pipeline())