import os
import httpx
from typing import List, Dict, Any, Optional

# Agmarknet Daily Wholesale Prices Resource ID on data.gov.in
DATA_GOV_IN_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_IN_BASE_URL = f"https://api.data.gov.in/resource/{DATA_GOV_IN_RESOURCE_ID}"

# Realistic benchmark fallback data (Uttar Pradesh / Central India APMC cluster)
# Used when DATA_GOV_IN_API_KEY is not configured or live API is temporarily unavailable
FALLBACK_MANDI_RATES = {
    "wheat": [
        {"market": "Kanpur", "district": "Kanpur", "state": "Uttar Pradesh", "modal_price": 2150, "distance_km": 15},
        {"market": "Unnao", "district": "Unnao", "state": "Uttar Pradesh", "modal_price": 2280, "distance_km": 42},
        {"market": "Fatehpur", "district": "Fatehpur", "state": "Uttar Pradesh", "modal_price": 2180, "distance_km": 65},
        {"market": "Barabanki", "district": "Barabanki", "state": "Uttar Pradesh", "modal_price": 2220, "distance_km": 80},
    ],
    "potato": [
        {"market": "Farrukhabad", "district": "Farrukhabad", "state": "Uttar Pradesh", "modal_price": 1150, "distance_km": 85},
        {"market": "Kanpur", "district": "Kanpur", "state": "Uttar Pradesh", "modal_price": 1280, "distance_km": 15},
        {"market": "Agra", "district": "Agra", "state": "Uttar Pradesh", "modal_price": 1210, "distance_km": 140},
    ],
    "mustard": [
        {"market": "Aligarh", "district": "Aligarh", "state": "Uttar Pradesh", "modal_price": 5400, "distance_km": 120},
        {"market": "Kanpur", "district": "Kanpur", "state": "Uttar Pradesh", "modal_price": 5250, "distance_km": 15},
        {"market": "Mathura", "district": "Mathura", "state": "Uttar Pradesh", "modal_price": 5550, "distance_km": 160},
    ]
}

# Standard rural transport freight benchmark: ₹1.5 per quintal per km (min ₹20/quintal)
FREIGHT_PER_QUINTAL_PER_KM = 1.5
MIN_FREIGHT_PER_QUINTAL = 20.0


def fetch_live_mandi_prices(
    commodity: str,
    state: Optional[str] = "Uttar Pradesh",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Queries live Agmarknet APMC mandi prices from data.gov.in.
    Falls back gracefully to benchmark regional data if no key is configured.
    """
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    commodity_normalized = commodity.strip().lower()

    if api_key:
        try:
            params = {
                "api-key": api_key,
                "format": "json",
                "limit": limit,
                "filters[commodity]": commodity.title(),
            }
            if state:
                params["filters[state]"] = state

            with httpx.Client(timeout=10.0) as client:
                res = client.get(DATA_GOV_IN_BASE_URL, params=params)
                if res.status_code == 200:
                    records = res.json().get("records", [])
                    if records:
                        return [
                            {
                                "market": r.get("market"),
                                "district": r.get("district"),
                                "state": r.get("state"),
                                "commodity": r.get("commodity"),
                                "variety": r.get("variety"),
                                "modal_price": float(r.get("modal_price", 0)),
                                "min_price": float(r.get("min_price", 0)),
                                "max_price": float(r.get("max_price", 0)),
                                "arrival_date": r.get("arrival_date"),
                                "source": "live_data_gov_in"
                            }
                            for r in records if r.get("modal_price")
                        ]
        except Exception:
            # Fall back to offline/cached dataset on network or key error
            pass

    # Fallback to local representative APMC cluster
    matched_key = next((k for k in FALLBACK_MANDI_RATES if k in commodity_normalized), "wheat")
    records = []
    for item in FALLBACK_MANDI_RATES[matched_key]:
        rec = dict(item)
        rec["commodity"] = commodity_normalized.title()
        rec["source"] = "apmc_benchmark_cluster"
        records.append(rec)
    return records


def calculate_mandi_arbitrage(
    mandi_records: List[Dict[str, Any]],
    distance_estimates: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes net realization (Mandi Rate - Transport Cost) across candidate mandis
    to determine the highest-profit market for the farmer.
    """
    arbitrage_table = []

    for r in mandi_records:
        market = r["market"]
        gross_rate = r["modal_price"]

        # Determine distance
        if distance_estimates and market in distance_estimates:
            dist = distance_estimates[market]
        else:
            dist = r.get("distance_km", 25.0)

        # Calculate transport cost
        transport_cost = max(MIN_FREIGHT_PER_QUINTAL, round(dist * FREIGHT_PER_QUINTAL_PER_KM, 2))
        net_rate = round(gross_rate - transport_cost, 2)

        arbitrage_table.append({
            "market": market,
            "district": r.get("district", ""),
            "gross_modal_price": gross_rate,
            "distance_km": dist,
            "transport_cost_per_quintal": transport_cost,
            "net_realization_per_quintal": net_rate
        })

    # Sort by highest net realization
    arbitrage_table.sort(key=lambda x: x["net_realization_per_quintal"], reverse=True)

    best_mandi = arbitrage_table[0] if arbitrage_table else None
    runner_up = arbitrage_table[1] if len(arbitrage_table) > 1 else None

    net_advantage = 0.0
    if best_mandi and runner_up:
        net_advantage = round(best_mandi["net_realization_per_quintal"] - runner_up["net_realization_per_quintal"], 2)

    return {
        "best_mandi": best_mandi,
        "runner_up": runner_up,
        "net_advantage_per_quintal": net_advantage,
        "all_mandis": arbitrage_table
    }
