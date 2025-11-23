from datamodel import Order, State
from collections import deque
import statistics

class Trader:
    def __init__(self):
        self.position_limit = 20
        self.history_window = 25
        self.mids_history = deque(maxlen=self.history_window)
        self.trade_size = 18  # Aggressive size
        
    def get_market_info(self, product, orderbook):
        if product not in orderbook:
            return None
        
        book = orderbook[product]
        if not book.buy_orders or not book.sell_orders:
            return None
        
        best_bid = max(book.buy_orders.keys())
        best_ask = min(book.sell_orders.keys())
        
        return {
            'best_bid': best_bid,
            'best_ask': best_ask,
            'mid': (best_bid + best_ask) / 2,
            'spread': best_ask - best_bid
        }
    
    def calculate_signal(self):
        """Calculate z-score and return directional signal"""
        if len(self.mids_history) < 15:
            return 0
        
        current = self.mids_history[-1]
        mean = statistics.mean(self.mids_history)
        
        try:
            std = statistics.stdev(self.mids_history)
            if std < 0.01:
                return 0
            
            z = (current - mean) / std
            
            # AGGRESSIVE thresholds - take positions on moderate signals
            if z > 1.0:
                return -1  # Rich - sell
            elif z > 0.5:
                return -0.5  # Slightly rich - small sell
            elif z < -1.0:
                return 1  # Cheap - buy
            elif z < -0.5:
                return 0.5  # Slightly cheap - small buy
            else:
                return 0
        except:
            return 0
    
    def run(self, state: State):
        orders = []
        product = "10K_NOTE"
        
        if product not in state.products:
            return orders
        
        market_info = self.get_market_info(product, state.orderbook)
        if not market_info:
            return orders
        
        best_bid = market_info['best_bid']
        best_ask = market_info['best_ask']
        mid = market_info['mid']
        spread = market_info['spread']
        
        self.mids_history.append(mid)
        
        pos = state.positions.get(product, 0)
        signal = self.calculate_signal()
        
        # Safer quote placement to avoid crossing
        if spread >= 6:
            our_bid = best_bid + 2
            our_ask = best_ask - 2
        elif spread >= 4:
            our_bid = best_bid + 1
            our_ask = best_ask - 1
        else:
            # Tight spread - join
            our_bid = best_bid
            our_ask = best_ask
        
        # Size based on signal
        bid_size = 15
        ask_size = 15
        
        if signal >= 1:  # Strong buy
            bid_size = 20
            ask_size = 8
        elif signal >= 0.5:
            bid_size = 18
            ask_size = 10
        elif signal <= -1:  # Strong sell
            bid_size = 8
            ask_size = 20
        elif signal <= -0.5:
            bid_size = 10
            ask_size = 18
        
        # Inventory management
        if pos > 10:
            bid_size = max(3, int(bid_size * 0.3))
            ask_size = 20
        elif pos < -10:
            bid_size = 20
            ask_size = max(3, int(ask_size * 0.3))
        
        # Place orders
        if pos < self.position_limit - 2 and bid_size > 0:
            orders.append(Order(product, our_bid, bid_size))
        
        if pos > -self.position_limit + 2 and ask_size > 0:
            orders.append(Order(product, our_ask, -ask_size))
        
        # Emergency unwind
        if pos >= 18:
            orders = [Order(product, best_bid, -20)]
        elif pos <= -18:
            orders = [Order(product, best_ask, 20)]
        
        return orders
