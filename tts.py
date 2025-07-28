import soundfile as sf
import subprocess   
import platform
import threading
from playsound import playsound
from kokoro import KPipeline

class VoiceTTS:
    def __init__(self, voice_file="audio.wav", model_id='prince-canuma/Kokoro-82M', lang='a'):
        self.pipeline = KPipeline(lang_code='a')  
        self.process = None
        self.voice_file = voice_file

    def voice_say(self, speaker, text, speed=1.0):
        # remove * from the text
        text = text.replace("*", "")
        for _, _, audio in self.pipeline(text, voice=speaker, speed=speed):
            if self.process is not None:
                self.process.join()
            sf.write(self.voice_file, audio, 24000)
            self.process = threading.Thread(target=playsound, args=[self.voice_file])
            self.process.start()

    def wait(self):
        if self.process is not None:
            self.process.join()
            self.process = None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Voice TTS system.")
    parser.add_argument("--voice", type=str, default="af_heart", help="Voice to use for TTS.")
    parser.add_argument("--text", type=str, default="Hello, this is a test of the voice TTS system.", help="Text to say.")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed of the speech.")
    parser.add_argument("--lang", type=str, default="a", help="a for English, z for Chinese.")
    args = parser.parse_args()  
    tts = VoiceTTS(lang=args.lang)
    tts.voice_say(args.voice, args.text, speed=args.speed)
    print("TTS started. Press Ctrl+C to stop.")
    tts.wait()
    print("TTS completed.")