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
        await voice_client.receive(sink=self.sink)
        
        logger.info("Started transcription")
    
    async def stop_transcription(self, voice_client):
        """Stop transcription"""
        if not self.is_transcribing:
            return
        
        self.is_transcribing = False
        if self.sink:
            self.sink.cleanup()
            self.sink = None
        voice_client.stop_receiving()
        logger.info("Stopped transcription")
    
    
    

class TranscriptionSink:
    """Custom audio sink for voice transcription"""
    def __init__(self, model, text_channel, loop, sample_rate):
        self.model = model
        self.text_channel = text_channel
        self.loop = loop
        self.sample_rate = sample_rate
        self.user_buffers = {}
        self.user_recognizers = {}
        self.user_names = {}
        self.chunk_size_48k = int(48000 * 5)  # 5 seconds at 48kHz mono
        self.min_chunk_48k = int(48000 * 1)   # 1 second at 48kHz mono
        logger.info("TranscriptionSink initialized")

    def write(self, user, data):
        user_id = str(user.id)
        if user_id not in self.user_names:
            self.user_names[user_id] = user.display_name

        if user_id not in self.user_buffers:
            self.user_buffers[user_id] = np.array([], dtype=np.int16)
            self.user_recognizers[user_id] = vosk.KaldiRecognizer(self.model, self.sample_rate)

        buffer = self.user_buffers[user_id]

        # Convert stereo 48kHz PCM to mono 48kHz
        pcm = np.frombuffer(data, dtype=np.int16)
        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]
        mono = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
        buffer = np.append(buffer, mono)

        # Process available chunks
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
                    coro = self.text_channel.send(f"🎤 **{self.user_names[user_id]}**: {text}")
                    asyncio.run_coroutine_threadsafe(coro, self.loop)
                    logger.info(f"Transcribed {self.user_names[user_id]}: {text}")

            buffer = buffer[self.chunk_size_48k:]

        self.user_buffers[user_id] = buffer

    def cleanup(self):
        logger.info("Cleaning up TranscriptionSink")
        self.user_buffers.clear()
        self.user_recognizers.clear()
        self.user_names.clear()

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