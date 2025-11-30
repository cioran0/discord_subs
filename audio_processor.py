import vosk
import logging
import asyncio
import io
import numpy as np
import discord
import tempfile
import os
import json
import wave
from discord.ext import commands
from discord.ext import voice_recv
import threading
import queue
import time


logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, model_path="models/vosk-model-small-en-us-0.15"):
        """Initialize the audio processor with Vosk model"""
        self.model = None
        self.model_path = model_path
        self.sample_rate = 16000  # Vosk preferred sample rate
        self.is_transcribing = False
        self.text_channel = None
        self.sink = None
        
    async def load_model(self):
        """Load the Vosk model asynchronously"""
        if self.model is None:
            logger.info(f"Loading Vosk model from: {self.model_path}")
            try:
                # Run in thread to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, 
                    vosk.Model, 
                    self.model_path
                )
                logger.info("Vosk model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Vosk model: {e}")
                raise
    
    async def start_transcription(self, voice_client, text_channel):
        """Start continuous transcription from voice channel"""
        if self.is_transcribing:
            return
        
        self.is_transcribing = True
        self.text_channel = text_channel
        await self.load_model()
        
        self.sink = TranscriptionSink(self.model, self.text_channel, asyncio.get_running_loop(), self.sample_rate)
        voice_client.listen(self.sink)
        
        logger.info("Started transcription")
    
    async def stop_transcription(self, voice_client):
        """Stop transcription"""
        if not self.is_transcribing:
            return
        
        self.is_transcribing = False
        if self.sink:
            self.sink.cleanup()
            self.sink = None
        voice_client.stop_listening()
        logger.info("Stopped transcription")
    
    
    

class TranscriptionSink(voice_recv.AudioSink):
    """Custom audio sink for voice transcription"""
    def __init__(self, model, text_channel, loop, sample_rate):
        super().__init__()
        self.model = model
        self.text_channel = text_channel
        self.loop = loop
        self.sample_rate = sample_rate
        self.user_buffers = {}
        self.user_recognizers = {}
        self.user_names = {}
        self.user_messages = {}  # Store message objects for editing
        self.chunk_size_48k = int(48000 * 3)  # 3 seconds at 48kHz mono
        self.min_chunk_48k = int(48000 * 1)   # 1 second at 48kHz mono
        logger.info("TranscriptionSink initialized")
    
    def wants_opus(self):
        """We want PCM data, not Opus"""
        return False

    def write(self, user, data):
        """Handle incoming audio data"""
        if user is None:
            return
            
        user_id = str(user.id)
        if user_id not in self.user_names:
            self.user_names[user_id] = user.display_name

        if user_id not in self.user_buffers:
            self.user_buffers[user_id] = np.array([], dtype=np.int16)
            self.user_recognizers[user_id] = vosk.KaldiRecognizer(self.model, self.sample_rate)

        buffer = self.user_buffers[user_id]

        # Get PCM data from VoiceData object
        if hasattr(data, 'pcm') and data.pcm:
            pcm_data = data.pcm
        else:
            return

        # Convert stereo 48kHz PCM to mono 48kHz
        pcm = np.frombuffer(pcm_data, dtype=np.int16)
        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]
        mono = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
        buffer = np.append(buffer, mono)

        # Process available chunks with overlap to avoid packet loss
        while len(buffer) >= self.min_chunk_48k:
            chunk_48k = buffer[:self.chunk_size_48k]
            # Simple decimation downsample to 16kHz (48kHz / 3 ≈ 16kHz)
            chunk_16k = chunk_48k[::3]
            raw_bytes = chunk_16k.astype(np.int16).tobytes()

            recognizer = self.user_recognizers[user_id]
            if recognizer.AcceptWaveform(raw_bytes):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').strip()
                if text:
                    if user_id in self.user_messages:
                        # Edit the partial message to become final
                        coro = self.user_messages[user_id].edit(content=f"🎤 **{self.user_names[user_id]}**: {text}")
                        asyncio.run_coroutine_threadsafe(coro, self.loop)
                        del self.user_messages[user_id]  # Remove from tracking
                    else:
                        # Send new final message
                        coro = self.text_channel.send(f"🎤 **{self.user_names[user_id]}**: {text}")
                        asyncio.run_coroutine_threadsafe(coro, self.loop)
                    logger.info(f"Transcribed {self.user_names[user_id]}: {text}")
            else:
                # Get partial results for intermediate feedback
                partial = json.loads(recognizer.PartialResult())
                partial_text = partial.get('partial', '').strip()
                if partial_text and len(partial_text) > 3:  # Only show meaningful partials
                    if user_id in self.user_messages:
                        # Edit existing message
                        coro = self.user_messages[user_id].edit(content=f"🎤 **{self.user_names[user_id]}*: {partial_text}")
                        asyncio.run_coroutine_threadsafe(coro, self.loop)
                    else:
                        # Create new message for partial
                        coro = self.text_channel.send(f"🎤 **{self.user_names[user_id]}*: {partial_text}")
                        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
                        try:
                            self.user_messages[user_id] = future.result(timeout=2)
                        except:
                            pass

            # Use 50% overlap to avoid missing audio between chunks
            buffer = buffer[self.chunk_size_48k // 2:]

        # Limit buffer size to prevent memory buildup
        max_buffer_size = self.chunk_size_48k * 4  # Keep max 8 seconds of audio
        if len(buffer) > max_buffer_size:
            buffer = buffer[-max_buffer_size:]
        
        self.user_buffers[user_id] = buffer

    def cleanup(self):
        logger.info("Cleaning up TranscriptionSink")
        # Finalize any remaining audio
        for user_id, recognizer in self.user_recognizers.items():
            if recognizer:
                final_result = json.loads(recognizer.FinalResult())
                text = final_result.get('text', '').strip()
                if text:
                    coro = self.text_channel.send(f"🎤 **{self.user_names[user_id]}**: {text}")
                    asyncio.run_coroutine_threadsafe(coro, self.loop)
                    logger.info(f"Final transcription {self.user_names[user_id]}: {text}")
        
        self.user_buffers.clear()
        self.user_recognizers.clear()
        self.user_names.clear()
        self.user_messages.clear()

    def idle(self):
        pass


def download_vosk_model():
    """Helper function to download a Vosk model"""
    import urllib.request
    import zipfile
    
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    model_path = "models"
    model_zip = "vosk-model-small-en-us-0.15.zip"
    
    if not os.path.exists(model_path):
        os.makedirs(model_path)
    
    if not os.path.exists(os.path.join(model_path, "vosk-model-small-en-us-0.15")):
        logger.info("Downloading Vosk model... This may take a while.")
        urllib.request.urlretrieve(model_url, model_zip)
        
        with zipfile.ZipFile(model_zip, 'r') as zip_ref:
            zip_ref.extractall(model_path)
        
        os.remove(model_zip)
        logger.info("Vosk model downloaded and extracted successfully")