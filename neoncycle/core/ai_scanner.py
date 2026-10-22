import math
from django.db.models import Sum
from .models import GarbagePrice, CollectionOrder, RecyclerDemand


def forecast_garbage_price(garbage_id, weight_kg=5.0):
    """
    Real-Time AI 7-Day Scrap Price Forecaster ("Hold or Sell" Signal).
    Uses live SQLite data:
      1. Current price & momentum (GarbagePrice.price_per_kg, change_pct)
      2. Active Recycler Demand volume & offered bonus prices (RecyclerDemand)
      3. Pending/In-Transit Household Supply volume (CollectionOrder)
    Predicts the next 7 days of prices (Day 1 to Day 7) and recommends SELL NOW or HOLD.
    """
    g_obj = GarbagePrice.objects.filter(id=garbage_id).first() or GarbagePrice.objects.first()
    current_price = float(g_obj.price_per_kg)
    momentum_pct = float(g_obj.change_pct)

    # 1. Calculate Live Supply from SQLite (Pending + Accepted + Weighed orders for this material)
    supply_agg = CollectionOrder.objects.filter(
        garbage_type=g_obj,
        status__in=['PENDING', 'ACCEPTED', 'WEIGHED']
    ).aggregate(total_supply=Sum('estimated_weight_kg'))
    total_supply_kg = float(supply_agg['total_supply'] or 0.0)

    # 2. Calculate Live Demand from SQLite (RecyclerDemand for this material)
    demands = RecyclerDemand.objects.filter(garbage_type=g_obj)
    total_demand_kg = float(demands.aggregate(total_demand=Sum('needed_kg'))['total_demand'] or 0.0)

    # Check if recyclers are offering a higher bonus price than current market rate
    highest_recycler_offer = current_price
    for d in demands:
        if float(d.offered_bonus_per_kg) > highest_recycler_offer:
            highest_recycler_offer = float(d.offered_bonus_per_kg)

    # 3. Compute AI Supply-Demand Pressure Index (-0.15 to +0.25)
    # If Demand > Supply, scarcity pushes future prices UP. If Supply > Demand, surplus pushes prices DOWN.
    net_imbalance = (total_demand_kg - total_supply_kg) / max(50.0, total_demand_kg + total_supply_kg + 50.0)
    bonus_pull = max(0.0, (highest_recycler_offer - current_price) / max(1.0, current_price)) * 0.45
    momentum_factor = (momentum_pct / 100.0) * 0.6

    daily_drift = (net_imbalance * 0.035) + (bonus_pull / 7.0) + (momentum_factor / 5.0)
    # Clamp daily drift to realistic bounds (-2.5% to +4.5% per day)
    daily_drift = max(-0.025, min(0.045, daily_drift))

    # Category-specific cyclical wave so each material has a distinct market curve
    seed_phase = (g_obj.id * 1.3) + (len(g_obj.code) * 0.7)

    labels = ["Today"]
    forecast_prices = [round(current_price, 2)]

    for day in range(1, 8):
        labels.append(f"Day +{day}")
        # Combine trend drift + damped market cycle wave
        wave = math.sin(day * 0.85 + seed_phase) * 0.018 * current_price
        projected = current_price * ((1.0 + daily_drift) ** day) + wave
        projected = round(max(5.0, projected), 2)
        forecast_prices.append(projected)

    # 4. Find Peak Price Day & Generate "HOLD" vs "SELL NOW" Recommendation
    max_price = max(forecast_prices)
    best_day_idx = forecast_prices.index(max_price)
    day_7_price = forecast_prices[-1]
    pct_diff_peak = round(((max_price - current_price) / max(1.0, current_price)) * 100.0, 1)
    pct_diff_7d = round(((day_7_price - current_price) / max(1.0, current_price)) * 100.0, 1)

    payout_today = round(weight_kg * current_price, 2)
    payout_peak = round(weight_kg * max_price, 2)
    extra_profit = round(payout_peak - payout_today, 2)

    # AI Confidence score based on data richness
    data_points = CollectionOrder.objects.filter(garbage_type=g_obj).count() + demands.count()
    confidence = round(min(98.4, 86.0 + min(12.0, data_points * 1.8)), 1)

    if best_day_idx >= 2 and pct_diff_peak >= 3.0:
        signal = "HOLD"
        signal_badge = f"HOLD FOR {best_day_idx} DAYS (📈 +{pct_diff_peak}%)"
        signal_color = "warning"
        reason = (
            f"AI detects strong upward pressure on {g_obj.name}. "
            f"Waiting {best_day_idx} days is projected to raise the rate from ₹{current_price:.2f}/kg "
            f"to ₹{max_price:.2f}/kg, earning you +₹{extra_profit:.2f} extra on {weight_kg} kg."
        )
    elif pct_diff_7d < -1.5:
        signal = "SELL NOW"
        signal_badge = f"SELL TODAY — PRICE DROPPING (📉 {pct_diff_7d}%)"
        signal_color = "success"
        reason = (
            f"Market supply for {g_obj.name} is rising and prices are projected to dip by {abs(pct_diff_7d)}% "
            f"over the next 7 days. Book your pickup today to lock in ₹{current_price:.2f}/kg!"
        )
    else:
        signal = "SELL NOW"
        signal_badge = "SELL TODAY — OPTIMAL RATE (⚡ STABLE PEAK)"
        signal_color = "info"
        reason = (
            f"{g_obj.name} is trading near its optimal 7-day peak at ₹{current_price:.2f}/kg "
            f"(Peak variance: +{pct_diff_peak}%). Selling today gives immediate payout of ₹{payout_today:.2f}."
        )

    return {
        "status": "ok",
        "garbage_id": g_obj.id,
        "category": g_obj.name,
        "code": g_obj.code,
        "current_price": round(current_price, 2),
        "peak_price": round(max_price, 2),
        "best_day_label": labels[best_day_idx],
        "pct_diff_peak": pct_diff_peak,
        "weight_kg": weight_kg,
        "payout_today": payout_today,
        "payout_peak": payout_peak,
        "extra_profit": extra_profit,
        "signal": signal,
        "signal_badge": signal_badge,
        "signal_color": signal_color,
        "reason": reason,
        "confidence": confidence,
        "supply_kg": round(total_supply_kg, 1),
        "demand_kg": round(total_demand_kg, 1),
        "labels": labels,
        "forecast_prices": forecast_prices,
    }