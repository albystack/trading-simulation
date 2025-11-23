from datamodel import Listing, Order, State
from collections import deque


class Trader:
    """
    Tutorial-round strategy for the single asset: 10K_NOTE.
    Uses rolling mean-reversion on mid-prices.

    Produces strong positive PnL on tutorial.csv.
    """

    def __init__(self):
        self.window = 50             # size of rolling mean/vol window
        self.mids = deque(maxlen=self.window)

        self.entry_z = 0.9           # more aggressive entry
        self.exit_z = 0.2            # quick flatten
        self.step = 5                # trade size per signal
        self.min_std = 1             # avoid division by small std

    def run(self, state: State):
        orders = []

        product = "10K_NOTE"

        # Check product exists
        if product not in state.products:
            return orders

        # Extract best bid/ask
        ob = state.orderbook.get(product)
        listings = Listing(ob, product)

        buy_book = listings.buy_orders
        sell_book = listings.sell_orders

        if not buy_book or not sell_book:
            return orders

        best_bid = max(buy_book.keys())
        best_ask = min(sell_book.keys())
        mid = (best_bid + best_ask) / 2

        # Update rolling mid history
        self.mids.append(mid)

        # Not enough data yet
        if len(self.mids) < self.window:
            return orders

        mean = sum(self.mids) / len(self.mids)
        var = sum((m - mean) ** 2 for m in self.mids) / len(self.mids)
        std = max(var ** 0.5, self.min_std)

        z = (mid - mean) / std

        pos = state.positions.get(product, 0)
        limit = state.pos_limit.get(product, 30)

        target = pos

        # Mean reversion logic:
        if abs(z) < self.exit_z:
            # Flatten quickly
            if pos > 0:
                target = max(0, pos - self.step)
            elif pos < 0:
                target = min(0, pos + self.step)

        else:
            # Buy dips
            if z <= -self.entry_z:
                target = min(limit, pos + self.step)

            # Sell rich
            if z >= self.entry_z:
                target = max(-limit, pos - self.step)

        delta = target - pos

        if delta > 0:
            orders.append(Order(product, best_ask, delta))
        elif delta < 0:
            orders.append(Order(product, best_bid, delta))

        return orders