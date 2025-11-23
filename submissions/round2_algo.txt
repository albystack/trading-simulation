from typing import Dict, List, Optional, Tuple
from datamodel import Order
import math

class Trader:
    """
    ETF1 Market Maker with Inventory Skew.

    - Calculates a 'fair value' for ETF1 based on the price of its constituent bonds.
    - Quotes bid/ask prices for ETF1 around this fair value.
    - Skews quotes aggressively based on ETF1 inventory to manage risk and encourage mean-reversion.
        - If long ETF1, quotes are pushed lower to incentivize selling.
        - If short ETF1, quotes are pushed higher to incentivize buying.
    - Captures the spread as a primary P&L source (market making).
    - Acts as a taker when the market offers a price better than our skewed reservation price,
      capturing immediate arbitrage opportunities.
    - ETF2 trading is disabled as it was in the original strategy.
    """

    def __init__(self):
        self.products = ["bond1", "bond2", "bond3", "bond4", "ETF1", "ETF2"]
        self.etf1_components = ["bond1", "bond2", "bond3"]
        self.max_pos_per_product = 40

        # ETF1 MM & Skew Parameters
        self.etf1_spread = 0.5  # Half-spread in ticks around fair value
        self.etf1_skew_intensity = 3.5  # Multiplier for how much inventory moves our price
        self.etf1_mm_qty = 5  # Quantity for market making orders

        # ETF2 parameters (off by default)
        self.enable_etf2 = False
        self.etf2_min_edge = 2.0
        self.etf2_max_per_tick = 4
        self.etf2_weights = {"bond1": 0.69, "bond2": 0.52, "bond4": 0.28}

    # ---------- Helpers ----------
    def _sorted_levels(
        self, price_volume: Dict[int, int], descending: bool
    ) -> List[Tuple[int, int]]:
        return sorted(
            [(int(p), int(v)) for p, v in price_volume.items() if v > 0],
            key=lambda x: x[0],
            reverse=descending,
        )

    def _prepare_books(
        self, orderbook: Dict[str, Dict[str, Dict[int, int]]]
    ) -> Dict[str, Dict[str, List[Tuple[int, int]]]]:
        books: Dict[str, Dict[str, List[Tuple[int, int]]]] = {}
        for product in self.products:
            ob = orderbook.get(product, {"BUY": {}, "SELL": {}})
            books[product] = {
                "BUY": self._sorted_levels(ob.get("BUY", {}), descending=True),
                "SELL": self._sorted_levels(ob.get("SELL", {}), descending=False),
            }
        return books

    def _get_best_price(self, book: List[Tuple[int, int]]) -> Optional[int]:
        return book[0][0] if book else None

    def _room_to_buy(self, product: str, positions: Dict[str, int]) -> int:
        return max(0, self.max_pos_per_product - positions.get(product, 0))

    def _room_to_sell(self, product: str, positions: Dict[str, int]) -> int:
        return max(0, self.max_pos_per_product + positions.get(product, 0))

    # ---------- ETF1 Strategy ----------
    def _trade_etf1(
        self, positions: Dict[str, int], books: Dict[str, Dict[str, List[Tuple[int, int]]]]
    ) -> List[Order]:
        orders: List[Order] = []

        # 1. Calculate Basket Prices (Fair Value)
        basket_buy_price = 0
        basket_sell_price = 0
        for bond in self.etf1_components:
            bond_ask = self._get_best_price(books[bond]["SELL"])
            bond_bid = self._get_best_price(books[bond]["BUY"])
            if bond_ask is None or bond_bid is None:
                return orders  # Not enough liquidity to make a price
            basket_buy_price += bond_ask
            basket_sell_price += bond_bid

        # 2. Calculate Inventory Skew
        etf1_pos = positions.get("ETF1", 0)
        # Normalized inventory skew: -1.0 (max short) to 1.0 (max long)
        inventory_skew = etf1_pos / self.max_pos_per_product

        # 3. Calculate Reservation Prices
        # Our reservation price is where we're indifferent to buying or selling.
        # It's based on the cost to hedge, our desired spread, and our inventory risk.
        # skew term: if long (skew > 0), we lower our prices. if short (skew < 0), we raise them.
        reservation_ask = basket_buy_price + self.etf1_spread - inventory_skew * self.etf1_skew_intensity
        reservation_bid = basket_sell_price - self.etf1_spread - inventory_skew * self.etf1_skew_intensity

        # 4. Generate Orders (Taker and Maker logic)
        etf1_best_ask = self._get_best_price(books["ETF1"]["SELL"])
        etf1_best_bid = self._get_best_price(books["ETF1"]["BUY"])

        # --- Buy ETF1 Side ---
        # Can we buy ETF1 and sell the basket?
        room_to_buy_etf = self._room_to_buy("ETF1", positions)
        if room_to_buy_etf > 0:
            # TAKER: Market ask is cheaper than our reservation bid -> immediate profit
            if etf1_best_ask is not None and etf1_best_ask < reservation_bid:
                # Can hedge by selling bonds
                can_hedge = all(self._room_to_sell(b, positions) > 0 for b in self.etf1_components)
                if can_hedge:
                    # Size is limited by position room and available volume
                    qty = min(room_to_buy_etf, books["ETF1"]["SELL"][0][1])
                    if qty > 0:
                        orders.append(Order("ETF1", etf1_best_ask, qty))
                        for bond in self.etf1_components:
                             # We sell bonds at the best bid to hedge
                            orders.append(Order(bond, self._get_best_price(books[bond]["BUY"]), -qty))

            # MAKER: Our bid is competitive, so post a new bid
            else:
                qty = min(room_to_buy_etf, self.etf1_mm_qty)
                orders.append(Order("ETF1", math.floor(reservation_bid), qty))

        # --- Sell ETF1 Side ---
        # Can we sell ETF1 and buy the basket?
        room_to_sell_etf = self._room_to_sell("ETF1", positions)
        if room_to_sell_etf > 0:
            # TAKER: Market bid is higher than our reservation ask -> immediate profit
            if etf1_best_bid is not None and etf1_best_bid > reservation_ask:
                # Can hedge by buying bonds
                can_hedge = all(self._room_to_buy(b, positions) > 0 for b in self.etf1_components)
                if can_hedge:
                    qty = min(room_to_sell_etf, books["ETF1"]["BUY"][0][1])
                    if qty > 0:
                        orders.append(Order("ETF1", etf1_best_bid, -qty))
                        for bond in self.etf1_components:
                            # We buy bonds at the best ask to hedge
                            orders.append(Order(bond, self._get_best_price(books[bond]["SELL"]), qty))
            # MAKER: Our ask is competitive, so post a new ask
            else:
                qty = min(room_to_sell_etf, self.etf1_mm_qty)
                orders.append(Order("ETF1", math.ceil(reservation_ask), -qty))

        return orders

    # ---------- Main ----------
    def run(self, state):
        books = self._prepare_books(state.orderbook)
        positions = dict(state.positions)

        # The new unified strategy for ETF1 handles all logic.
        # Any existing orders are implicitly cancelled by the simulator.
        orders: List[Order] = self._trade_etf1(positions, books)

        return orders