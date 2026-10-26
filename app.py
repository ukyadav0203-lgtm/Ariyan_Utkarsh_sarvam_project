import os
import sys
from pathlib import Path
import streamlit as st

# Configure page
st.set_page_config(
    page_title="MandiMitra | Spoken Crop Advisory & Arbitrage",
    page_icon="🌾",
    layout="wide"
)

# Load secrets from Streamlit Cloud or local .env
if "SARVAM_API_KEY" in st.secrets:
    os.environ["SARVAM_API_KEY"] = st.secrets["SARVAM_API_KEY"]
if "DATA_GOV_IN_API_KEY" in st.secrets:
    os.environ["DATA_GOV_IN_API_KEY"] = st.secrets["DATA_GOV_IN_API_KEY"]

# Fallback to local .env
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists() and "SARVAM_API_KEY" not in os.environ:
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("SARVAM_API_KEY="):
                os.environ["SARVAM_API_KEY"] = line.strip().split("=", 1)[1].strip()

import mandi_service
import mandimitra_pipeline

# Custom CSS for clean UI
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #2E7D32; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #555; margin-bottom: 25px; }
    .metric-card { background: #F1F8E9; border-radius: 10px; padding: 15px; border-left: 5px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌾 MandiMitra (मंडी मित्र)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Spoken Crop Advisory & Real-Time APMC Price Arbitrage powered by <b>Sarvam AI</b></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("🗣️ Farmer Voice Query")
    
    # Pre-set query buttons for quick evaluation
    sample_queries = [
        "भैया, गेंहू का आज क्या भाव है? कानपुर या उन्नाव में से कहाँ बेचने पर ज्यादा मुनाफा होगा?",
        "आलू की फसल निकालनी है, फर्रुखाबाद और कानपुर मंडी में क्या भाव चल रहा है?",
        "सरसों बेचने के लिए अलीगढ़ मंडी सही रहेगी या मथुरा? भाड़ा काट के कहाँ फायदा है?"
    ]
    
    selected_sample = st.selectbox("Or choose a sample farmer query:", ["Type custom query..."] + sample_queries)
    
    if selected_sample == "Type custom query...":
        query_text = st.text_area("Farmer voice / text message:", value="भैया, गेंहू का आज क्या भाव है? कानपुर या उन्नाव में से कहाँ बेचने पर ज्यादा मुनाफा होगा?", height=100)
    else:
        query_text = selected_sample
        st.info(f"Selected: {query_text}")

    audio_file = st.file_uploader("Or upload a farmer voice note (.mp3, .wav):", type=["mp3", "wav", "m4a", "ogg"])

    run_btn = st.button("🚀 Analyze & Generate Spoken Advisory", type="primary", use_container_width=True)

with col2:
    st.subheader("💡 Spoken Advisory & Arbitrage Results")

    if run_btn:
        if not os.getenv("SARVAM_API_KEY"):
            st.error("Please configure SARVAM_API_KEY in your environment or Streamlit Secrets!")
        else:
            with st.spinner("Processing with Sarvam Saaras & Sarvam-105B..."):
                try:
                    # 1. Intent extraction
                    intent = mandimitra_pipeline.extract_crop_and_location(query_text)
                    commodity = intent.get("commodity", "wheat")
                    state = intent.get("state", "Uttar Pradesh")
                    
                    st.success(f"🎯 **Detected Crop:** {commodity.title()} | **State:** {state}")

                    # 2. Mandi lookup & arbitrage
                    records = mandi_service.fetch_live_mandi_prices(commodity=commodity, state=state)
                    arbitrage = mandi_service.calculate_mandi_arbitrage(records)

                    best = arbitrage["best_mandi"]
                    runner = arbitrage["runner_up"]
                    adv = arbitrage["net_advantage_per_quintal"]

                    # Display metrics
                    m1, m2 = st.columns(2)
                    with m1:
                        st.metric(
                            label=f"⭐ Best Mandi: {best['market']}",
                            value=f"₹{best['net_realization_per_quintal']}/q",
                            delta=f"+₹{adv}/q Net Profit"
                        )
                    with m2:
                        if runner:
                            st.metric(
                                label=f"Comparison: {runner['market']}",
                                value=f"₹{runner['net_realization_per_quintal']}/q",
                                delta=f"-₹{adv}/q Difference",
                                delta_color="inverse"
                            )

                    # 3. Advisory text
                    advisory_text = mandimitra_pipeline.generate_spoken_advisory(query_text, "hi-IN", arbitrage)
                    st.markdown("### 💬 Spoken Advisory Message:")
                    st.info(f"*{advisory_text}*")

                    # 4. Audio synthesis via Bulbul
                    with st.spinner("Synthesizing audio with Sarvam Bulbul..."):
                        audio_path = mandimitra_pipeline.synthesize_voice_reply(advisory_text, "hi-IN", output_path="web_reply.mp3")
                        st.markdown("### 🔊 Listen to Return Voice Note:")
                        with open(audio_path, "rb") as af:
                            st.audio(af.read(), format="audio/mp3")

                    # Comparison table
                    st.markdown("#### 📊 Nearby Mandi Transport & Net Profit Matrix")
                    table_data = [
                        {
                            "Mandi": m["market"],
                            "Gross Rate": f"₹{m['gross_modal_price']}",
                            "Distance": f"{m['distance_km']} km",
                            "Transport Deduction": f"-₹{m['transport_cost_per_quintal']}",
                            "Net In-Hand Profit": f"₹{m['net_realization_per_quintal']}"
                        }
                        for m in arbitrage["all_mandis"]
                    ]
                    st.table(table_data)

                except Exception as e:
                    st.error(f"Error executing pipeline: {e}")
    else:
        st.write("Click the button above to run the pipeline and generate the voice note.")
