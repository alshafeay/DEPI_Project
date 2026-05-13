import json
import os
from faster_whisper import WhisperModel


def transcribe_audio(
    audio_path="data/test/sample_audio.wav",
    output_path="data/processed/transcript.json",
    model_size="small",
    device="cpu",
    compute_type="int8"
):
    """
    Convert English audio into English text with timestamps.
    """

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print("Loading ASR model...")

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type
    )

    print("Transcribing audio...")

    segments, info = model.transcribe(
        audio_path,
        language="en",
        beam_size=5
    )

    transcript_segments = []

    for i, segment in enumerate(segments):
        transcript_segments.append({
            "id": i,
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text_en": segment.text.strip()
        })

    transcript_data = {
        "language": "en",
        "duration": round(info.duration, 2),
        "segments": transcript_segments
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(transcript_data, file, ensure_ascii=False, indent=4)

    print(f"Transcript saved to: {output_path}")

    return transcript_data


if __name__ == "__main__":
    transcribe_audio()