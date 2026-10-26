import os
import sys
import json
import base64
from pathlib import Path

# Fix Windows console UTF-8 encoding for Hindi and emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load .env variables before importing Sarvam
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                if val:
                    os.environ[key.strip()] = val

from sarvamai import SarvamAI
import mandi_service

# Initialize Sarvam AI Client
client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))


def transcribe_voice_note(audio_file_path: str):
    """
    Step 1: Uses Sarvam Saaras to transcribe speech in local dialects.
    """
    print(f"🎤 [Saaras STT] Processing voice note from: {audio_file_path}")
    with open(audio_file_path, "rb") as f:
        response = client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
            language_code="unknown",  # Auto-detects dialect / Indic language
            mode="transcribe"
        )
    print(f"   Transcribed text: \"{response.transcript}\"")
    print(f"   Detected language: {response.language_code}")
    return response.transcript, response.language_code


def extract_crop_and_location(farmer_query: str) -> dict:
    """
    Step 2a: Uses Sarvam-105B to extract crop and location intent from farmer query.
    """
    extraction_prompt = f"""
    You are an agricultural intent parser. Extract the crop/commodity and farmer location from the farmer's query.
    Respond ONLY with a valid JSON object with keys: "commodity", "state", "farmer_district".
    Default state to "Uttar Pradesh" if not mentioned.

    Farmer query: "{farmer_query}"
    """

    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": "You are a precise JSON extractor. Output valid JSON only, no markdown or extra text."},
            {"role": "user", "content": extraction_prompt}
        ],
        temperature=0.1,
        max_tokens=128
    )

    raw_text = response.choices[0].message.content.strip()
    try:
        # Strip potential markdown formatting
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1].strip()
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
        data = json.loads(raw_text)
    except Exception:
        # Fallback if raw text wasn't strict JSON
        data = {"commodity": "wheat", "state": "Uttar Pradesh", "farmer_district": "Kanpur"}

    return data


def generate_spoken_advisory(farmer_query: str, detected_lang: str, arbitrage: dict) -> str:
    """
    Step 2b: Uses Sarvam-105B to synthesize the arbitrage calculation into a respectful, spoken advisory.
    """
    best = arbitrage["best_mandi"]
    runner = arbitrage["runner_up"]
    adv = arbitrage["net_advantage_per_quintal"]

    system_instruction = f"""
    You are 'MandiMitra' (मंडी मित्र), a trustworthy, knowledgeable agricultural companion speaking directly to a farmer.
    
    Arbitrage facts to communicate:
    - Recommended Mandi: {best['market']} (Gross rate: ₹{best['gross_modal_price']}/quintal, Transport: ₹{best['transport_cost_per_quintal']}/quintal, Net realization: ₹{best['net_realization_per_quintal']}/quintal)
    - Comparison Mandi: {runner['market']} (Gross rate: ₹{runner['gross_modal_price']}/quintal, Transport: ₹{runner['transport_cost_per_quintal']}/quintal, Net realization: ₹{runner['net_realization_per_quintal']}/quintal)
    - Net Profit Gain: ₹{adv}/quintal higher in {best['market']} after transport deductions.

    Guidelines:
    1. Reply in natural, spoken conversational style in the SAME language/dialect as the query (e.g. colloquial Hindi / Bhojpuri loan words if query was Hindi).
    2. Keep it concise (2-3 sentences), warm, and clear for a voice note.
    3. State the numbers clearly so the farmer knows exactly why traveling to {best['market']} makes financial sense.
    """

    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": farmer_query}
        ],
        temperature=0.3,
        max_tokens=256
    )

    return response.choices[0].message.content.strip()


def synthesize_voice_reply(advisory_text: str, language_code: str, output_path: str = "mandimitra_reply.mp3") -> str:
    """
    Step 3: Uses Sarvam Bulbul to generate high-quality conversational audio.
    """
    print(f"🔊 [Bulbul TTS] Synthesizing audio response...")

    # Select speaker based on language for bulbul:v3
    speaker = "aditya"
    lang = "hi-IN"

    if language_code == "ta-IN":
        speaker = "gokul"
        lang = "ta-IN"

    response = client.text_to_speech.convert(
        text=advisory_text,
        language_code=lang,
        speaker=speaker,
        model="bulbul:v3",
        output_audio_codec="mp3"
    )

    audio_bytes = base64.b64decode(response.audios[0])
    out_file = Path(__file__).resolve().parent / output_path
    with open(out_file, "wb") as f:
        f.write(audio_bytes)

    print(f"   Audio saved successfully to: {out_file}")
    return str(out_file)


def run_mandimitra(audio_path: str = None, text_query: str = None):
    """
    Orchestrates the entire MandiMitra pipeline.
    """
    print("=" * 65)
    print("🌾 MandiMitra: Spoken Crop Advisory & Mandi Price Arbitrage")
    print("=" * 65)

    # 1. Speech-to-Text (Saaras) or Direct Test Query
    if audio_path and os.path.exists(audio_path):
        query_text, lang_code = transcribe_voice_note(audio_path)
    else:
        query_text = text_query or "भैया, गेंहू का आज क्या भाव है? कानपुर या उन्नाव में से कहाँ बेचने पर ज्यादा मुनाफा होगा?"
        lang_code = "hi-IN"
        print(f"📝 [Simulated Voice Query]: \"{query_text}\"")

    # 2. Extract Intent
    print("\n🔍 [Sarvam-105B] Extracting crop and location...")
    intent = extract_crop_and_location(query_text)
    commodity = intent.get("commodity", "wheat")
    state = intent.get("state", "Uttar Pradesh")
    print(f"   Parsed Commodity: {commodity.title()} | State: {state}")

    # 3. Live APMC Mandi Lookup & Arbitrage Engine
    print(f"\n📊 [Agmarknet Engine] Fetching mandi rates for '{commodity}'...")
    mandi_records = mandi_service.fetch_live_mandi_prices(commodity=commodity, state=state)
    arbitrage = mandi_service.calculate_mandi_arbitrage(mandi_records)

    print("   Arbitrage Matrix:")
    for m in arbitrage["all_mandis"]:
        print(f"   • {m['market']:<12}: Gross ₹{m['gross_modal_price']}/q | Transport: ₹{m['transport_cost_per_quintal']}/q | Net: ₹{m['net_realization_per_quintal']}/q")

    # 4. Generate Spoken Advisory
    print("\n💡 [Sarvam-105B] Formulating spoken advisory in native dialect...")
    advisory = generate_spoken_advisory(query_text, lang_code, arbitrage)
    print(f"   Advisory: \"{advisory}\"")

    # 5. Text-to-Speech (Bulbul)
    print("\n🎧 [Bulbul TTS] Generating audio message...")
    audio_file = synthesize_voice_reply(advisory, lang_code)

    print("\n" + "=" * 65)
    print(f"✅ Pipeline Completed! Return voice note: {audio_file}")
    print("=" * 65)
    return advisory, audio_file


if __name__ == "__main__":
    run_mandimitra()
