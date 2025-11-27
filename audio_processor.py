import vosk
import logging
import asyncio
import io
import numpy as np
from pydub import AudioSegment
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
        self.is_transcribing = False
        self.audio_buffer = []
        self.buffer_duration = 30  # Process audio in 30-second chunks
        self.sample_rate = 16000  # Vosk preferred sample rate
        self.text_channel = None
        self.audio_queue = queue.Queue()
        self.processing_thread = None
        
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
        
        # Start the audio processing thread
        self.processing_thread = threading.Thread(target=self._process_audio_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start receiving audio using the voice client's audio stream
        voice_client.listen(self._on_audio_receive)
        
        logger.info("Started transcription")
    
    async def stop_transcription(self, voice_client):
        """Stop transcription"""
        if not self.is_transcribing:
            return
        
        self.is_transcribing = False
        voice_client.stop_listening()
        
        # Wait for processing thread to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        logger.info("Stopped transcription")
    
    def _on_audio_receive(self, data, user):
        """Callback for received audio data"""
        if self.is_transcribing:
            # Put audio data in queue for processing
            self.audio_queue.put((data, user))
    
    def _process_audio_queue(self):
        """Process audio data from queue in separate thread"""
        recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        
        while self.is_transcribing:
            try:
                # Get audio data from queue with timeout
                data, user = self.audio_queue.get(timeout=1)
                
                # Process audio synchronously in this thread
                self._process_audio_chunk_sync(data, recognizer)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing thread: {e}")
    
    def _process_audio_chunk_sync(self, audio_data, recognizer):
        """Process audio chunk synchronously"""
        try:
            # Convert audio data to format suitable for Vosk
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=2,  # 16-bit
                frame_rate=48000,  # Discord's sample rate
                channels=2  # Stereo
            )
            
            # Convert to mono and 16kHz (Vosk's preferred format)
            audio_segment = audio_segment.set_channels(1).set_frame_rate(self.sample_rate)
            
            # Convert to raw audio data
            audio_data = audio_segment.raw_data
            
            # Process audio with Vosk
            if recognizer.AcceptWaveform(audio_data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '')
                
                # Send transcription to Discord channel (schedule in main thread)
                if text.strip():
                    asyncio.run_coroutine_threadsafe(
                        self.text_channel.send(f"🎤 **Transcription:** {text}"),
                        self.text_channel.guild.me.client.loop
                    )
                    logger.info(f"Transcribed: {text}")
            else:
                # Partial result (for real-time feedback)
                partial = json.loads(recognizer.PartialResult())
                partial_text = partial.get('partial', '')
                if partial_text.strip() and len(partial_text) > 10:  # Only show meaningful partials
                    asyncio.run_coroutine_threadsafe(
                        self.text_channel.send(f"🎤 **Listening:** {partial_text}..."),
                        self.text_channel.guild.me.client.loop
                    )
                    
        except Exception as e:
            logger.error(f"Error processing audio: {e}")

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