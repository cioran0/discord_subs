import discord
import asyncio
import logging
from discord.ext import commands
from discord.ext import voice_recv
import os
from dotenv import load_dotenv
from audio_processor import AudioProcessor, download_vosk_model


# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = '?'

# Initialize bot with minimal intents to avoid privileged intent requirements
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
# Note: message_content is a privileged intent - enable it in your Discord Developer Portal for this bot application
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, case_insensitive=True)

# Global audio processor
audio_processor = AudioProcessor()

@bot.event
async def on_ready():
    """Event triggered when the bot is ready"""
    logger.info(f'{bot.user.name} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} servers')

@bot.command(name='subbyjoin', help='Join the voice channel you are in')
async def join_voice(ctx):
    """Join the voice channel of the user who called the command"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        try:
            await channel.connect(cls=voice_recv.VoiceRecvClient)
            await ctx.send(f"by cioran 0 Joined {channel.name}")
            logger.info(f"Joined voice channel: {channel.name}")
        except discord.ClientException:
            await ctx.send("Already in a voice channel!")
    else:
        await ctx.send("You need to be in a voice channel to use this command!")

@bot.command(name='subbyleave', help='Leave the current voice channel')
async def leave_voice(ctx):
    """Leave the current voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel")
        logger.info("Left voice channel")
    else:
        await ctx.send("I'm not in a voice channel!")

@bot.command(name='subbystart', help='Start transcribing audio in the voice channel')
async def start_transcription(ctx):
    """Start transcribing audio from the voice channel"""
    if ctx.voice_client:
        try:
            await audio_processor.start_transcription(ctx.voice_client, ctx.channel)
            await ctx.send("🎙️ Started transcription! I'll now transcribe speech in this voice channel.")
        except Exception as e:
            await ctx.send(f"❌ Error starting transcription: {str(e)}")
            logger.error(f"Error starting transcription: {e}")
    else:
        await ctx.send("I need to be in a voice channel first! Use !subbyjoin")

@bot.command(name='subbystop', help='Stop transcribing audio')
async def stop_transcription(ctx):
    """Stop transcribing audio"""
    if ctx.voice_client:
        try:
            await audio_processor.stop_transcription(ctx.voice_client)
            await ctx.send("🛑 Stopped transcription.")
        except Exception as e:
            await ctx.send(f"❌ Error stopping transcription: {str(e)}")
            logger.error(f"Error stopping transcription: {e}")
    else:
        await ctx.send("I'm not transcribing in any voice channel!")

@bot.command(name='setup', help='Download Vosk model for speech recognition')
async def setup_model(ctx):
    """Download the Vosk model for speech recognition"""
    await ctx.send("📥 Downloading Vosk model... This may take a few minutes.")
    try:
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_vosk_model)
        await ctx.send("✅ Vosk model downloaded successfully! You can now use !start to begin transcription.")
    except Exception as e:
        await ctx.send(f"❌ Error downloading model: {str(e)}")
        logger.error(f"Error downloading model: {e}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        exit(1)
    
    bot.run(BOT_TOKEN)