import re
with open("scripts/macro_workbench.py", "r") as f:
    text = f.read()

new_code = """def _regime_label(dimension: str, value: float | None, display: str, signal_id: str) -> tuple[str, float, float]:
    if value is None:
        return "insufficient data", 50.0, 0.0

    display_l = str(display).lower()
    sid_l = str(signal_id).lower()
    if "y/y" in display_l or "yoy" in sid_l:
        transform = "yoy"
    elif "m/m" in display_l or "mom" in sid_l:
        transform = "mom"
    elif "q/q" in display_l or "qoq" in sid_l:
        transform = "qoq"
    else:
        transform = "level"

    confidence = 1.0
    if transform in {"mom", "qoq"}:
        confidence = 0.8  # Noisier fast frequency

    if dimension == "growth":
        if transform == "mom":
            if value >= 0.4: return "above-trend expansion", 80.0, confidence
            if value >= 0.1: return "moderate expansion", 65.0, confidence
            if value >= 0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence
        elif transform == "qoq":
            if value >= 1.0: return "above-trend expansion", 80.0, confidence
            if value >= 0.3: return "moderate expansion", 65.0, confidence
            if value >= 0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence
        elif transform == "level":
            # e.g., PMI
            if value >= 52: return "above-trend expansion", 80.0, confidence
            if value >= 50: return "moderate expansion", 65.0, confidence
            return "contraction", 25.0, confidence
        else: # yoy
            if value >= 3: return "above-trend expansion", 80.0, confidence
            if value >= 1: return "moderate expansion", 65.0, confidence
            if value >= 0: return "stall-speed growth", 45.0, confidence
            return "contraction", 25.0, confidence

    if dimension == "inflation":
        if transform == "mom":
            if value >= 0.4: return "inflation pressure", 25.0, confidence
            if value >= 0.2: return "above-target inflation", 45.0, confidence
            if value >= 0.1: return "near-target inflation", 70.0, confidence
            return "disinflation risk", 55.0, confidence
        else:
            if value >= 5: return "inflation pressure", 25.0, confidence
            if value >= 3: return "above-target inflation", 45.0, confidence
            if value >= 1: return "near-target inflation", 70.0, confidence
            return "disinflation risk", 55.0, confidence

    if dimension == "policy":
        if value >= 5: return "restrictive stance", 35.0, confidence
        if value >= 3: return "neutral-tight stance", 55.0, confidence
        return "easy stance", 65.0, confidence

    if dimension == "external":
        if transform == "level" and "balance" in sid_l:
            # Often nominal balance; a simple sign check
            if value >= 0: return "external strength", 75.0, confidence
            return "external drag", 35.0, confidence
        else:
            if value >= 3: return "external strength", 75.0, confidence
            if value <= -3: return "external drag", 35.0, confidence
            return "balanced external impulse", 60.0, confidence

    if dimension == "fiscal":
        if value <= -6: return "fiscal stress", 30.0, confidence
        if value <= -3: return "watch fiscal slippage", 45.0, confidence
        return "fiscal contained", 65.0, confidence

    if dimension == "financial":
        if value >= 8: return "tight financial conditions", 35.0, confidence
        if value <= -5: return "credit deleveraging", 40.0, confidence
        return "financial conditions stable", 60.0, confidence

    if dimension == "property":
        if value >= 5: return "property hot", 65.0, confidence
        if value < 0: return "property drag", 35.0, confidence
        return "property stable", 58.0, confidence

    return "tracked", 50.0, confidence


def _country_quality_score(card: dict[str, Any]) -> dict[str, Any]:
    charts = float(card.get("charts") or 0)
    expected = float(card.get("expected") or charts or 1)
    coverage = _score(charts / expected * 100.0 if expected else 0.0)
    proxy_penalty = min(float(card.get("proxy_fills") or 0) * 20.0, 60.0)
    gap_penalty = min(float(card.get("gaps_or_dropped") or 0) * 2.5, 30.0)
    freshness = card.get("freshness_summary") or {}
    current = float(freshness.get("current") or 0)
    freshness_charts = float(freshness.get("charts") or charts or 1)
    freshness_score = _score(current / freshness_charts * 100.0 if freshness_charts else 0.0)
    low_confidence = float(freshness.get("low_confidence") or 0)
    low_penalty = min(low_confidence * 2.0, 20.0)
    score = _score(coverage * 0.35 + freshness_score * 0.35 + 30.0 - proxy_penalty - gap_penalty - low_penalty)
    if score >= 80:
        label = "high-confidence dashboard"
    elif score >= 60:
        label = "usable with watch-list"
    else:
        label = "needs data review"
    return {
        "score": round(score, 1),
        "label": label,
        "coverage_score": round(coverage, 1),
        "freshness_score": round(freshness_score, 1),
        "proxy_penalty": round(proxy_penalty, 1),
        "gap_penalty": round(gap_penalty, 1),
    }


def _regime_for_card(card: dict[str, Any]) -> dict[str, Any]:
    signals = card.get("signals") or {}
    dimensions: dict[str, dict[str, Any]] = {}
    
    cyc_scores, cyc_weights = [], []
    str_scores, str_weights = [], []
    
    cyclical_dims = {"growth", "inflation", "policy", "external"}
    structural_dims = {"fiscal", "financial", "property"}
    
    for dimension in ("growth", "inflation", "policy", "external", "fiscal", "financial", "property"):
        signal = signals.get(dimension, {})
        value = _number(signal.get("value") if signal else None)
        display = signal.get("display") or ""
        sig_id = signal.get("id") or ""
        
        label, score, weight = _regime_label(dimension, value, display, sig_id)
        dimensions[dimension] = {
            "label": label,
            "score": round(score, 1),
            "confidence_weight": weight,
            "value": value,
            "display": display or (f"{value:.2f}" if value is not None else "n/a"),
            "source_signal": sig_id,
        }
        if value is not None and weight > 0:
            if dimension in cyclical_dims:
                cyc_scores.append(score * weight)
                cyc_weights.append(weight)
            elif dimension in structural_dims:
                str_scores.append(score * weight)
                str_weights.append(weight)
                
    quality = _country_quality_score(card)
    
    cyc_total_weight = sum(cyc_weights) if cyc_weights else 0
    str_total_weight = sum(str_weights) if str_weights else 0
    
    cyclical_score = sum(cyc_scores) / cyc_total_weight if cyc_total_weight > 0 else 50.0
    structural_score = sum(str_scores) / str_total_weight if str_total_weight > 0 else 50.0
    
    composite = _score((cyclical_score + structural_score) / 2)
    
    if composite >= 70:
        composite_label = "constructive"
    elif composite >= 50:
        composite_label = "mixed"
    else:
        composite_label = "defensive"
        
    return {
        "composite_score": round(composite, 1),
        "cyclical_score": round(cyclical_score, 1),
        "structural_score": round(structural_score, 1),
        "composite_label": composite_label,
        "quality": quality,
        "dimensions": dimensions,
"""

target = re.compile(r"def _regime_label\(dimension: str, value: float \| None\) -> tuple\[str, float\]:.*?return {\n        \"composite_score\": round\(composite, 1\),\n        \"composite_label\": composite_label,\n        \"quality\": quality,\n        \"dimensions\": dimensions,", re.DOTALL)
text = target.sub(new_code + "\n    }", text)

with open("scripts/macro_workbench.py", "w") as f:
    f.write(text)
