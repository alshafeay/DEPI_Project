import os
import argparse
from audio_processing.asr import transcribe_audio
from translation_tts.translator import translate_transcript


def build_output_paths(audio_path):
    """
    Create unique output names based on the audio file name.
    Example:
    data/processed/steve_harvey.wav
    ->
    data/processed/steve_harvey_transcript.json
    data/processed/steve_harvey_translated.json
    """
    audio_name = os.path.splitext(os.path.basename(audio_path))[0]

    transcript_path = f"data/processed/{audio_name}_transcript.json"
    translated_path = f"data/processed/{audio_name}_translated.json"

    return transcript_path, translated_path


def main():
    parser = argparse.ArgumentParser(
        description="Audio to Text + Translation Pipeline"
    )

    parser.add_argument(
        "--audio",
        type=str,
        default="data/processed/steve_harvey.wav",
        help="Path to the input audio file"
    )

    args = parser.parse_args()

    audio_path = args.audio
    transcript_path, translated_path = build_output_paths(audio_path)

    print("=" * 50)
    print("Audio to Text + Translation Pipeline")
    print("=" * 50)

    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return

    print(f"\nInput audio: {audio_path}")
    print(f"Transcript output: {transcript_path}")
    print(f"Translated output: {translated_path}")

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