# 🌾 MandiMitra: Spoken Crop Advisory & Mandi Price Arbitrage

> **Empowering smallholder farmers with voice-first APMC mandi intelligence in their native Indian dialects.**

---

## 💡 The Problem
Smallholder farmers in India often sell their produce in local village markets at discounted rates because:
1. They lack real-time price discovery across nearby regulated APMC mandis.
2. Dashboards and text-heavy apps are inaccessible to farmers who prefer speaking in their local dialect over typing.
3. Higher mandi rates in neighboring districts are often misleading unless travel and freight costs are factored into net profit.

## 🚀 The Solution
**MandiMitra** is a voice-in, voice-out agricultural intelligence pipeline powered by **Sarvam AI** and **Agmarknet (Open Government Data)**:
- **Speech-to-Text (Saaras)**: Transcribes the farmer's voice query in Hindi, Bhojpuri, or Tamil.
- **Reasoning Engine (Sarvam-105B Conversations)**: Extracts crop & location intent, queries daily APMC prices, and calculates net realization after deducting transport freight.
- **Text-to-Speech (Bulbul)**: Synthesizes a warm, respectful, conversational audio reply in the farmer's native dialect.

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart LR
    A["Farmer Voice Note\n(Hindi / Bhojpuri / Tamil)"] --> B["1. Saaras (STT)\nspeech_to_text.transcribe"]
    B --> C["Transcribed Text\n+ Detected Language"]
    C --> D["2. Sarvam-105B Conversations\nEntity Extraction\n(Crop, State, District)"]
    D --> E["3. Agmarknet Engine\nLive APMC Prices +\nTransport Deductions"]
    E --> F["4. Sarvam-105B Conversations\nSpoken Advisory Generation"]
    F --> G["5. Bulbul (TTS)\ntext_to_speech.convert"]
    G --> H["Return Voice Note\n(.mp3)"]
```

---

## 📦 Project Structure

```
├── .env.example             # Template for API keys
├── .gitignore               # Ensures sensitive .env is never pushed
├── requirements.txt         # Project dependencies
├── main.py                  # Minimal working Sarvam AI test call
├── mandi_service.py         # Agmarknet APMC price lookup & transport arbitrage engine
├── mandimitra_pipeline.py   # Full end-to-end voice-to-voice orchestrator
└── README.md                # Project documentation
```

---

## ⚡ Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/mandimitra.git
cd mandimitra
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and add your Sarvam AI key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
SARVAM_API_KEY=your_sarvam_api_key
DATA_GOV_IN_API_KEY=your_optional_data_gov_in_key
```

### 3. Run MandiMitra
```bash
python mandimitra_pipeline.py
```

The pipeline will analyze market rates across neighboring mandis, calculate net realization, and generate `mandimitra_reply.mp3`.

---

## 🛠️ Built With
- [Sarvam AI](https://sarvam.ai) — Sovereign AI models for Indian Languages (Saaras, Sarvam-105B, Bulbul)
- [data.gov.in](https://data.gov.in) — Directorate of Marketing & Inspection (Agmarknet)
