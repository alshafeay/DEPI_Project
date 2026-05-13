import os
from audio_processing.asr import transcribe_audio
from translation_tts.translator import translate_transcript


def main():
    """
    Main pipeline for Donia's stage:
    1. Convert English audio to English transcript using ASR.
    2. Translate English transcript to natural Arabic dubbing script using Llama.
    """

    audio_path = "data/test/sample_audio.wav"
    transcript_path = "data/processed/transcript.json"
    translated_path = "data/processed/translated_transcript.json"

    print("=" * 50)
    print("Audio to Text + Translation Pipeline")
    print("=" * 50)

    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return

    print("\nStep 1: Transcribing audio...")
    transcribe_audio(
        audio_path=audio_path,
        output_path=transcript_path
    )

    print("\nStep 2: Translating transcript...")
    translate_transcript(
        input_path=transcript_path,
        output_path=translated_path
    )

    print("\nPipeline completed successfully!")
    print(f"Transcript saved at: {transcript_path}")
    print(f"Translated transcript saved at: {translated_path}")


if __name__ == "__main__":
    main()