from datamodel import Listing, Order, State
from collections import deque
import statistics


class Trader:
    """
    Round 2: ETF Arbitrage + Market Making
    
    Key insights from analysis:
    - ETF1 ≈ 1.02*bond1 + 1.00*bond2 + 1.04*bond3 (R² = 0.92)
    - ETF2 ≈ 0.71*bond1 + 0.52*bond2 + 0.28*bond4 (R² = 0.97)
    - bond4 has MASSIVE 20-tick spread (all others 1-tick)
    - ETFs have 50x more liquidity than bonds
    - ETF deviation from fair value: std ~4.4 (ETF1), ~1.6 (ETF2)
    
    Strategy:
    1. Calculate fair value of ETFs based on bond prices
    2. Market make aggressively on ETFs when fairly priced
    3. Take directional positions when ETFs deviate significantly
    4. Exploit bond4's huge spread when hedging
    """

    def __init__(self):
        self.window = 30
        self.mids_history = {}
        
        # ETF composition weights (from regression)
        self.etf1_weights = {
            'bond1': 1.02,
            'bond2': 1.00,
            'bond3': 1.04,
            'bond4': -0.05
        }
        
        self.etf2_weights = {
            'bond1': 0.71,
            'bond2': 0.52,
            'bond3': 0.01,
            'bond4': 0.28
        }
        
        # Trading parameters by product
        self.params = {
            'ETF1': {
                'base_size': 25,
                'max_size': 35,
                'inv_threshold': 35,
                'is_etf': True
            },
            'ETF2': {
                'base_size': 25,
                'max_size': 35,
                'inv_threshold': 35,
                'is_etf': True
            },
            'bond1': {
                'base_size': 3,
                'max_size': 5,
                'inv_threshold': 8,
                'is_etf': False
            },
            'bond2': {
                'base_size': 3,
                'max_size': 5,
                'inv_threshold': 8,
                'is_etf': False
            },
            'bond3': {
                'base_size': 3,
                'max_size': 5,
                'inv_threshold': 8,
                'is_etf': False
            },
            'bond4': {
                'base_size': 8,
                'max_size': 12,
                'inv_threshold': 12,
                'is_etf': False
            }
        }

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

    def calculate_etf_fair_value(self, product, bond_mids):
        """Calculate theoretical ETF price from bond prices"""
        if product == 'ETF1':
            weights = self.etf1_weights
        elif product == 'ETF2':
            weights = self.etf2_weights
        else:
            return None
        
        # Need all bond prices
        required_bonds = ['bond1', 'bond2', 'bond3', 'bond4']
        if not all(b in bond_mids for b in required_bonds):
            return None
        
        fair_value = sum(weights[bond] * bond_mids[bond] for bond in required_bonds)
        return fair_value

    def run(self, state: State):
        orders = []
        
        # Initialize history
        for product in state.products:
            if product not in self.mids_history:
                self.mids_history[product] = deque(maxlen=self.window)
        
        # Get all market info first
        market_data = {}
        bond_mids = {}
        
        for product in state.products:
            info = self.get_market_info(product, state.orderbook)
            if info:
                market_data[product] = info
                self.mids_history[product].append(info['mid'])
                
                if 'bond' in product:
                    bond_mids[product] = info['mid']
        
        # Trade each product
        for product in state.products:
            if product not in market_data:
                continue
            
            info = market_data[product]
            mid = info['mid']
            best_bid = info['best_bid']
            best_ask = info['best_ask']
            spread = info['spread']
            
            params = self.params[product]
            pos = state.positions.get(product, 0)
            limit = state.pos_limit.get(product, 50)
            
            # Calculate fair value for ETFs
            fair_value = None
            fv_deviation = 0
            if params['is_etf']:
                fair_value = self.calculate_etf_fair_value(product, bond_mids)
                if fair_value:
                    fv_deviation = mid - fair_value
            
            # Determine quote prices
            if params['is_etf'] and spread == 1:
                # ETFs: tight spread - be aggressive
                our_bid = best_bid
                our_ask = best_ask
            elif spread >= 20:
                # bond4: huge spread - go way inside
                our_bid = best_bid + 8
                our_ask = best_ask - 8
            elif spread >= 4:
                # Medium spread
                our_bid = best_bid + 1
                our_ask = best_ask - 1
            else:
                # Join
                our_bid = best_bid
                our_ask = best_ask
            
            # Size determination
            base_size = params['base_size']
            max_size = params['max_size']
            inv_threshold = params['inv_threshold']
            
            buy_size = base_size
            sell_size = base_size
            
            # ETF arbitrage adjustment
            if params['is_etf'] and fair_value:
                if fv_deviation > 2:  # ETF rich - sell more
                    sell_size = max_size
                    buy_size = max(3, int(base_size * 0.5))
                elif fv_deviation < -2:  # ETF cheap - buy more
                    buy_size = max_size
                    sell_size = max(3, int(base_size * 0.5))
            
            # Increase size on wide spreads (more profit)
            if spread >= 20:
                buy_size = min(max_size, int(base_size * 1.3))
                sell_size = min(max_size, int(base_size * 1.3))
            
            # Inventory management
            if pos > inv_threshold:
                our_bid = best_bid - 1
                our_ask = best_ask - 1
                buy_size = max(2, int(buy_size * 0.3))
                sell_size = min(max_size + 3, int(sell_size * 1.8))
            elif pos < -inv_threshold:
                our_bid = best_bid + 1
                our_ask = best_ask + 1
                buy_size = min(max_size + 3, int(buy_size * 1.8))
                sell_size = max(2, int(sell_size * 0.3))
            elif pos > inv_threshold * 0.6:
                buy_size = int(buy_size * 0.7)
                sell_size = int(sell_size * 1.2)
            elif pos < -inv_threshold * 0.6:
                buy_size = int(buy_size * 1.2)
                sell_size = int(sell_size * 0.7)
            
            # Emergency at limits
            if pos >= limit - 3:
                our_ask = best_bid + 1
                buy_size = 0
                sell_size = min(max_size, limit + pos)
            elif pos <= -limit + 3:
                our_bid = best_ask - 1
                sell_size = 0
                buy_size = min(max_size, limit - pos)
            
            # Place orders - PASSIVE only
            if buy_size > 0 and pos < limit:
                actual_buy = min(buy_size, limit - pos)
                if actual_buy > 0 and our_bid < best_ask:
                    orders.append(Order(product, int(our_bid), int(actual_buy)))
            
            if sell_size > 0 and pos > -limit:
                actual_sell = min(sell_size, limit + pos)
                if actual_sell > 0 and our_ask > best_bid:
                    orders.append(Order(product, int(our_ask), -int(actual_sell)))
        
        return orders
