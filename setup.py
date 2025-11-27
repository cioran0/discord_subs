"""
Setup script for Discord Subtitle Bot
"""
import os
import sys
from audio_processor import download_vosk_model

def main():
    """Setup the Discord subtitle bot"""
    print("🤖 Discord Subtitle Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version}")
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            with open('.env.example', 'r') as example:
                with open('.env', 'w') as env:
                    env.write(example.read())
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env and add your Discord bot token!")
        else:
            print("❌ .env.example file not found!")
            sys.exit(1)
    else:
        print("✅ .env file exists")
    
    # Create models directory
    if not os.path.exists('models'):
        os.makedirs('models')
        print("✅ Created models directory")
    
    # Ask about downloading Vosk model
    download_model = input("\n📥 Download Vosk speech recognition model? (y/n): ").lower().strip()
    
    if download_model in ['y', 'yes']:
        print("Downloading Vosk model... This may take a few minutes.")
        try:
            download_vosk_model()
            print("✅ Vosk model downloaded successfully!")
        except Exception as e:
            print(f"❌ Error downloading model: {e}")
            print("You can download it manually later using the !setup command in Discord")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your Discord bot token")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the bot: python bot.py")
    print("4. Invite the bot to your Discord server")
    print("5. Use !join, !start commands in Discord")

if __name__ == "__main__":
    main()