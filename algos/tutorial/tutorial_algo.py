from datamodel import Listing, Order, State
from collections import deque
import statistics


class Trader:
    """
    Tutorial: ULTRA-AGGRESSIVE Market Making Strategy
    
    Key insights from data analysis:
    - Spread: 4-6 ticks (67% are 4, 33% are 6)
    - EXTREME mean reversion: -0.49 lag-1 autocorr
    - Price range: 9997-10003 (only 6 ticks total!)
    - Low bot competition (0.79 avg volume)
    - Market making works VERY well here
    
    Strategy:
    - MAXIMUM SIZE quoting (up to position limit)
    - Always go 1-2 ticks inside spread
    - Use mean reversion for directional tilt
    - Rapid inventory management
    """

    def __init__(self):
        self.window = 20  # Even shorter
        self.mids_history = deque(maxlen=self.window)
        
        # MAXIMUM AGGRESSION
        self.base_size = 28        # HUGE base size
        self.max_size = 30         # At the limit
        self.inv_threshold = 16    # Slightly higher threshold
        
    def get_market_info(self, product, orderbook):
        ob = orderbook.get(product)
        if not ob or not ob["BUY"] or not ob["SELL"]:
            return None
        
        best_bid = max(ob["BUY"].keys())
        best_ask = min(ob["SELL"].keys())
        
        return {
            'mid': (best_bid + best_ask) / 2,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': best_ask - best_bid
        }

    def calculate_mean_reversion_signal(self):
        """Calculate strong mean reversion signal"""
        if len(self.mids_history) < 15:
            return 0
        
        current = self.mids_history[-1]
        mean = statistics.mean(self.mids_history)
        
        try:
            std = statistics.stdev(self.mids_history)
            if std < 0.01:
                return 0
            
            z = (current - mean) / std
            
            # Strong signal thresholds
            if z > 1.2:
                return -2  # Very rich - sell aggressively
            elif z > 0.6:
                return -1  # Rich - sell
            elif z < -1.2:
                return 2   # Very cheap - buy aggressively
            elif z < -0.6:
                return 1   # Cheap - buy
            else:
                return 0   # Neutral
        except:
            return 0

    def run(self, state: State):
        orders = []
        
        # Tutorial only has one product
        product = "10K_NOTE"
        
        if product not in state.products:
            return orders
        
        market_info = self.get_market_info(product, state.orderbook)
        if not market_info:
            return orders
        
        mid = market_info['mid']
        best_bid = market_info['best_bid']
        best_ask = market_info['best_ask']
        spread = market_info['spread']
        
        # Update history
        self.mids_history.append(mid)
        
        pos = state.positions.get(product, 0)
        limit = state.pos_limit.get(product, 20)
        
        # Mean reversion signal
        mr_signal = self.calculate_mean_reversion_signal()
        
        # Quote placement - BALANCED AGGRESSION
        if spread >= 6:
            # Wide spread - go 2 ticks inside
            our_bid = best_bid + 2
            our_ask = best_ask - 2
        elif spread >= 5:
            # Medium spread - go 2 ticks inside
            our_bid = best_bid + 2
            our_ask = best_ask - 2
        elif spread == 4:
            # Standard spread - go 1 tick inside
            our_bid = best_bid + 1
            our_ask = best_ask - 1
        else:
            # Tight spread - join
            our_bid = best_bid
            our_ask = best_ask
        
        # Size determination - START BIG
        buy_size = self.base_size
        sell_size = self.base_size
        
        # Mean reversion size adjustment
        if mr_signal >= 2:  # Very cheap
            buy_size = self.max_size
            sell_size = max(10, int(sell_size * 0.5))
        elif mr_signal == 1:  # Cheap
            buy_size = min(self.max_size, int(buy_size * 1.3))
            sell_size = max(12, int(sell_size * 0.7))
        elif mr_signal == -1:  # Rich
            sell_size = min(self.max_size, int(sell_size * 1.3))
            buy_size = max(12, int(buy_size * 0.7))
        elif mr_signal <= -2:  # Very rich
            sell_size = self.max_size
            buy_size = max(10, int(buy_size * 0.5))
        
        # Inventory management - MODERATE REBALANCING
        if pos > self.inv_threshold:
            # Long - want to sell
            our_bid = best_bid  # Pull back bid
            our_ask = best_ask - 1  # Aggressive ask
            buy_size = max(5, int(buy_size * 0.3))
            sell_size = min(self.max_size, int(sell_size * 1.8))
            
        elif pos < -self.inv_threshold:
            # Short - want to buy
            our_bid = best_bid + 1  # Aggressive bid
            our_ask = best_ask  # Pull back ask
            buy_size = min(self.max_size, int(buy_size * 1.8))
            sell_size = max(5, int(sell_size * 0.3))
        
        # Moderate inventory tilt
        elif pos > 8:
            buy_size = int(buy_size * 0.6)
            sell_size = int(sell_size * 1.4)
        elif pos < -8:
            buy_size = int(buy_size * 1.4)
            sell_size = int(sell_size * 0.6)
        
        # Emergency at limits
        if pos >= limit - 2:
            # Must sell NOW
            our_ask = best_ask - 1
            buy_size = 0
            sell_size = min(limit + pos, self.max_size)
        elif pos <= -limit + 2:
            # Must buy NOW
            our_bid = best_bid + 1
            sell_size = 0
            buy_size = min(limit - pos, self.max_size)
        
        # Place orders - ALWAYS PASSIVE
        if buy_size > 0 and pos < limit:
            actual_buy = min(buy_size, limit - pos)
            if actual_buy > 0 and our_bid < best_ask:
                orders.append(Order(product, int(our_bid), int(actual_buy)))
        
        if sell_size > 0 and pos > -limit:
            actual_sell = min(sell_size, limit + pos)
            if actual_sell > 0 and our_ask > best_bid:
                orders.append(Order(product, int(our_ask), -int(actual_sell)))
        
        return orders
