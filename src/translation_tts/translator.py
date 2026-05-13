import json
import os
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.1:8b"


def merge_segments(segments, max_chars=900, max_duration=35):
    """
    Merge small ASR segments into larger chunks before translation.
    This gives Llama more context.
    """

    merged = []
    current_text = ""
    current_start = None
    current_end = None
    current_ids = []

    for segment in segments:
        text = segment["text_en"].strip()

        if not text:
            continue

        if current_start is None:
            current_start = segment["start"]

        current_ids.append(segment["id"])
        current_end = segment["end"]

        current_text = (current_text + " " + text).strip()

        duration = current_end - current_start

        too_long_text = len(current_text) >= max_chars
        too_long_duration = duration >= max_duration

        if too_long_text or too_long_duration:
            merged.append({
                "id": len(merged),
                "source_segment_ids": current_ids,
                "start": round(current_start, 2),
                "end": round(current_end, 2),
                "text_en": current_text
            })

            current_text = ""
            current_start = None
            current_end = None
            current_ids = []

    if current_text:
        merged.append({
            "id": len(merged),
            "source_segment_ids": current_ids,
            "start": round(current_start, 2),
            "end": round(current_end, 2),
            "text_en": current_text
        })

    return merged


def build_prompt(english_text):
    """
    Strong prompt for Arabic dubbing script rewriting.
    """

    return f"""
You are a professional Arabic dubbing script writer.

Your task is NOT literal translation.
Your task is to rewrite the English speech into a natural Arabic dubbing script.

The English text may contain ASR mistakes, so understand the intended meaning from context.

Important rules:
- Return ONLY Arabic text.
- Do NOT explain anything.
- Do NOT translate word by word.
- Rewrite the meaning naturally in Arabic.
- Use fluent Modern Standard Arabic.
- Make it sound natural when spoken aloud.
- Keep the motivational tone.
- Keep it concise and suitable for text-to-speech.
- Do not use awkward literal phrases.

Avoid these bad Arabic expressions:
- "لدي كل شخص"
- "تحمله في ذهنك"
- "ضمان الإقلاع"
- "تحت الشمس"
- "ترتجع"

Use these natural meanings:
- Everybody has a turn back moment = يمر كل شخص بلحظة تراجع
- go forward = يمضي قدمًا / يواصل الطريق
- give up = يستسلم
- before you give up = قبل أن تستسلم
- the guarantee is it will never happen = الاستسلام يضمن أن ما تريده لن يحدث أبدًا
- quitting = الاستسلام
- no matter what = مهما كانت الظروف

Example style:
يمر كل شخص بلحظة تراجع، لحظة يختار فيها إما أن يمضي قدمًا أو يستسلم. لكن قبل أن تستسلم، تذكّر أن الاستسلام يضمن لك أن ما تريده لن يحدث أبدًا. أما طالما أنك لم تستسلم، فستبقى فرصة النجاح موجودة مهما كانت الظروف.

Now rewrite this English speech into natural Arabic dubbing text:

{english_text}

Arabic dubbing script only:
""".strip()


def translate_with_llama(english_text):
    """
    Send English text to local Llama through Ollama API.
    """

    payload = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "system",
            "content": "You are a professional Arabic dubbing translator. You always return only fluent Arabic text without explanations."
        },
        {
            "role": "user",
            "content": build_prompt(english_text)
        }
    ],
    "stream": False,
    "options": {
        "temperature": 0.0,
        "top_p": 0.7,
        "repeat_penalty": 1.15
    }
}

    response = requests.post(OLLAMA_URL, json=payload, timeout=180)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error: {response.status_code} - {response.text}")

    result = response.json()
    arabic_text = result["message"]["content"].strip()

    return arabic_text


def translate_transcript(
    input_path="data/processed/transcript.json",
    output_path="data/processed/translated_transcript.json"
):
    """
    Translate transcript from English to Arabic using local Llama.
    """

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Transcript file not found: {input_path}")

    print("Loading transcript...")

    with open(input_path, "r", encoding="utf-8") as file:
        transcript_data = json.load(file)

    print("Merging ASR segments...")
    merged_segments = merge_segments(transcript_data["segments"])

    translated_segments = []

    print("Translating with local Llama...")

    for segment in merged_segments:
        english_text = segment["text_en"]

        arabic_text = translate_with_llama(english_text)

        translated_segments.append({
            "id": segment["id"],
            "source_segment_ids": segment["source_segment_ids"],
            "start": segment["start"],
            "end": segment["end"],
            "text_en": english_text,
            "text_ar": arabic_text
        })

        print(f"Chunk {segment['id']} translated.")

    translated_data = {
        "source_language": "en",
        "target_language": "ar",
        "model": MODEL_NAME,
        "translation_type": "context_aware_dubbing_translation",
        "duration": transcript_data.get("duration"),
        "segments": translated_segments
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(translated_data, file, ensure_ascii=False, indent=4)

    print(f"Translated transcript saved to: {output_path}")

    return translated_data


if __name__ == "__main__":
    translate_transcript()