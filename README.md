# Discord Subtitle Bot

A Discord bot that provides real-time speech-to-text transcription for voice channels using Vosk (offline speech recognition).

## Features

- 🎙️ Real-time voice channel transcription
- 💻 Offline speech recognition (no API costs)
- 🌍 Multiple language support (with different Vosk models)
- ⚙️ Easy setup and configuration
- 📝 Displays transcriptions as Discord messages

## Prerequisites

- Python 3.8 or higher
- FFmpeg (required for audio processing)
- Discord Bot Token

## Installation

1. **Clone or download this project**

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note:** If you encounter PyNaCl installation issues on Windows:
   - Install Visual C++ Build Tools first
   - Or use: `pip install --upgrade pip setuptools wheel` then `pip install PyNaCl`

4. **Install FFmpeg:**
   - **Windows:** Download from [FFmpeg official site](https://ffmpeg.org/download.html) and add to PATH
   - **macOS:** `brew install ffmpeg`
   - **Linux:** `sudo apt-get install ffmpeg` (Ubuntu/Debian)

5. **Set up Discord Bot:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Enable "Server Members Intent" (Message Content Intent is NOT required)
   - Copy the bot token

6. **Configure the bot:**
   - Copy `.env.example` to `.env`
   - Fill in your Discord bot token:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

7. **Download speech recognition model:**
   - Run the bot once and use the `!setup` command in Discord
   - Or manually download a model from [Vosk Models](https://alphacephei.com/vosk/models)

## Usage

1. **Invite the bot to your server** with the following OAuth2 scopes and bot permissions:

   **OAuth2 URL Generator Settings:**
   - Scopes: `bot` and `applications.commands`
   
   **Bot Permissions:**
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Send Messages in Threads
   - ✅ Embed Links
   - ✅ Connect
   - ✅ Speak
   - ✅ Use Voice Activity
   - ✅ Read Message History (optional, for better context)

   **Generate the invite URL:**
   - Go to Discord Developer Portal → Your Application → OAuth2 → URL Generator
   - Select the scopes and permissions above
   - Copy the generated URL and use it to invite the bot

   **Note:** Message Content Intent is NOT required. The bot uses minimal intents to avoid privileged intent requirements.

2. **Start the bot:**
   ```bash
   python bot.py
   ```

3. **Bot Commands:**
   - `!join` - Join your current voice channel
   - `!leave` - Leave the voice channel
   - `!start` - Start transcribing audio in the voice channel
   - `!stop` - Stop transcribing
   - `!setup` - Download the Vosk model (first-time setup)

## How It Works

1. The bot joins a voice channel when commanded
2. It captures audio from the voice channel
3. Audio is processed and converted to the format Vosk expects
4. Vosk performs offline speech recognition
5. Transcriptions are sent as Discord messages in real-time

## Language Support

The bot supports multiple languages through different Vosk models. To change languages:

1. Download a different model from [Vosk Models](https://alphacephei.com/vosk/models)
2. Place it in the `models/` directory
3. Update the `model_path` in `audio_processor.py`

Available models include:
- English (small, medium, large)
- German, French, Spanish, Italian, Portuguese, Chinese, Russian, and more

## Troubleshooting

**Bot won't start:**
- Check that your Discord token is correct in `.env`
- Ensure all dependencies are installed
- Verify FFmpeg is installed and in your PATH

**Transcription not working:**
- Make sure you've downloaded the Vosk model using `!setup`
- Check that the bot has permission to connect to voice channels
- Ensure the bot is in the same voice channel as the speakers

**Poor transcription quality:**
- Try a larger Vosk model (medium or large)
- Ensure clear audio quality in the voice channel
- Check that the correct language model is being used

## Configuration Options

You can modify these settings in `audio_processor.py`:

- `model_path`: Path to the Vosk model
- `sample_rate`: Audio sample rate (default: 16000)
- `buffer_duration`: Audio chunk processing duration

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.