CRYPTO_BASE_ASSETS = {
    "BTC",
    "ETH",
    "SOL",
    "ADA",
    "XRP",
    "LTC",
    "DOGE",
    "BNB",
    "AVAX",
    "DOT",
    "LINK",
}

SYMBOL_BASE_PRICES = {
    "EURUSD": 1.0850,
    "GBPUSD": 1.2700,
    "USDJPY": 156.20,
    "BTCUSD": 67000.0,
    "ETHUSD": 3200.0,
    "SOLUSD": 150.0,
    "ADAUSD": 0.46,
    "XRPUSD": 0.54,
}


def infer_asset_class(symbol: str) -> str:
    upper = symbol.upper()
    if len(upper) >= 6 and upper.endswith(("USD", "USDT", "USDC")):
        base = upper[:-3] if upper.endswith("USD") else upper[:-4]
        if base in CRYPTO_BASE_ASSETS:
            return "crypto"
    return "fx"


def price_precision(symbol: str) -> int:
    upper = symbol.upper()
    if infer_asset_class(upper) == "crypto":
        return 2
    if upper.endswith("JPY"):
        return 3
    return 5


def initial_price(symbol: str) -> float:
    upper = symbol.upper()
    known = SYMBOL_BASE_PRICES.get(upper)
    if known is not None:
        return known
    if infer_asset_class(upper) == "crypto":
        return 100.0
    if upper.endswith("JPY"):
        return 150.0
    return 1.0


def spread_amount(symbol: str, mid_price: float) -> float:
    if infer_asset_class(symbol) == "crypto":
        # 5 bps minimum spread of 0.10 to keep crypto quotes realistic.
        return max(mid_price * 0.0005, 0.10)
    if symbol.upper().endswith("JPY"):
        return 0.01
    return 0.0001


def step_amount(symbol: str, mid_price: float) -> float:
    if infer_asset_class(symbol) == "crypto":
        # Larger walk for volatile crypto instruments.
        return max(mid_price * 0.0015, 0.5)
    if symbol.upper().endswith("JPY"):
        return 0.08
    return max(mid_price * 0.0002, 0.00005)
