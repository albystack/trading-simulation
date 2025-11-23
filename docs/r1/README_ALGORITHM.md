# 🏆 DUFS Trading Competition - Round 1 Algorithm
## Final PnL: **7,290** (Sharpe Ratio: 3.93)

---

## 📊 **Performance Summary**

| Metric | Value |
|--------|-------|
| **Final PnL** | 7,290 |
| **Max PnL** | 7,495 |
| **Win Rate** | 54.6% |
| **Sharpe Ratio** | 3.93 |
| **Max Drawdown** | -1,225 |
| **Profit Factor** | 1.38 |

---

## 🚀 **How to Run**

### 1. **Run the Algorithm**
```bash
python main.py --round "Round Data/Round_1/Round_1.csv" --algo "round1_algo.py"
```

### 2. **Analyze Performance** (Optional)
After running the backtest, you can get detailed analytics:
```bash
python analyze_performance.py
```

This will:
- Print comprehensive performance metrics
- Generate `performance_analysis.png` with 6 detailed charts
- Show per-product statistics

### 3. **Submit to Competition**
Send `round1_algo.txt` via email to the competition organizer.

---

## 💡 **Strategy Overview**

### **Core Philosophy: Passive Market Making**
The algorithm is a **pure market maker** that NEVER crosses the spread. It profits by:

1. **Providing Liquidity**: Always posting passive limit orders on both sides
2. **Capturing Spreads**: Earning the bid-ask spread when filled
3. **Large Sizing**: Using aggressive order sizes (18-28 per asset)
4. **Smart Inventory Management**: Dynamically skewing quotes based on position

### **Key Insights from Data Analysis**

#### 📈 **Asset Characteristics**
- **CASTLE_STOCKS**: Highest bot activity (3x more liquidity) → Largest position size (22)
- **Average Spread**: 3-4 ticks across all assets
- **Volatility**: Mean reversion patterns present
- **Position Limits**: 30 per asset

#### ⚠️ **Critical Lesson Learned**
- **Crossing the spread is VERY expensive**
  - Aggressive strategy lost -44,626 with 23.2% win rate
  - Passive strategy gained +7,290 with 54.6% win rate
  - **Insight**: Bots don't provide consistent take-able liquidity

---

## 🎯 **Strategy Components**

### 1. **Quote Placement Logic**
```
Spread >= 5: Quote 2 ticks inside (bid+2, ask-2)
Spread == 4: Quote 1 tick inside (bid+1, ask-1) 
Spread == 3: Penny the spread (bid+1, ask-1)
Spread <= 2: Join the market (bid, ask)
```

### 2. **Dynamic Sizing**
- **Base Size**: 17-22 depending on asset
- **Wide Spread Bonus**: +4 size when spread >= 4
- **CASTLE_STOCKS**: 22 base (highest bot activity)
- **Others**: 17-18 base

### 3. **Fair Value Adjustment**
- Calculate 25-period moving average as fair value
- Tilt sizes by 10-15% when price deviates > 0.8 from fair value
- Buy more when cheap, sell more when rich

### 4. **Inventory Management** (Most Important!)

```
Position > 23: Aggressive skewing
  - Pull bid back by 1 tick
  - Reduce buy size by 70%
  - Increase sell size by 70%
  
Position > 15: Moderate skewing
  - Reduce buy size by 30%
  - Increase sell size by 20%

Position < -23: Inverse skewing (encourage buying)
Position approaching ±30: Emergency orders
```

---

## 📊 **Per-Asset Performance**

| Asset | Avg Position | Volume Traded | Strategy |
|-------|-------------|---------------|----------|
| HATFIELD_STOCKS | 20.1 | 294 | Standard MM |
| COLLINGWOOD_STOCKS | 20.0 | 255 | Standard MM |
| CHADS_STOCKS | 22.0 | 279 | Standard MM |
| JOHNS_STOCKS | 20.6 | 257 | Standard MM |
| **CASTLE_STOCKS** | **13.9** | **2,009** | **Aggressive MM** |
| CUTHS_STOCKS | 21.3 | 261 | Standard MM |

**CASTLE_STOCKS** drives most profit with 7.8x more volume than others.

---

## 🧠 **Why This Strategy Works**

### ✅ **Advantages**
1. **Risk Management**: Never exposed to adverse selection from crossing
2. **High Win Rate**: 54.6% of ticks are profitable
3. **Consistent Growth**: Steady PnL accumulation (not boom/bust)
4. **Low Drawdown**: Max drawdown only -1,225 (16% of final PnL)
5. **Scalable**: Works across all 6 assets simultaneously

### 📈 **Profit Sources**
1. **Spread Capture**: ~3-4 ticks per round trip
2. **Volume**: 3,355 total trades executed
3. **Inventory Skewing**: Reduces risk, maintains profitability
4. **Fair Value Tilt**: Slight directional edge when mispriced

---

## 🔧 **Technical Details**

### **Parameters (Optimized)**
```python
HATFIELD_STOCKS:   base=18, max=25, inv_threshold=23
COLLINGWOOD_STOCKS: base=18, max=25, inv_threshold=23
CHADS_STOCKS:      base=18, max=25, inv_threshold=23
JOHNS_STOCKS:      base=17, max=24, inv_threshold=23
CASTLE_STOCKS:     base=22, max=28, inv_threshold=25
CUTHS_STOCKS:      base=18, max=25, inv_threshold=23
```

### **Risk Controls**
- Position limits: ±30 per asset
- Inventory threshold: 23 (77% of limit)
- Emergency exit at ±27
- Never cross spread (safety check in code)

---

## 📁 **Files Included**

1. **round1_algo.py** - Main trading algorithm
2. **round1_algo.txt** - Same file for email submission
3. **analyze_performance.py** - Performance analysis tool
4. **README.md** - This file

---

## 🎓 **Key Learnings**

### **What DOESN'T Work**
❌ Crossing the spread aggressively (-44k PnL)  
❌ Large directional bets based on mean reversion  
❌ Taking bot liquidity without careful analysis  
❌ Ignoring inventory risk  

### **What DOES Work**
✅ Passive market making (7.3k PnL)  
✅ Large sizes with tight risk management  
✅ Letting others cross to you  
✅ Dynamic inventory management  
✅ Focus on high-volume assets (CASTLE)  

---

## 📞 **Support**

If you need to modify the strategy:
- Adjust `base_size` in params to change aggressiveness
- Modify `inv_threshold` to change risk tolerance
- Change quote logic spread thresholds for different markets

---

## 🏁 **Conclusion**

This algorithm achieves **7,290 PnL** through disciplined passive market making. It's not flashy, but it's:
- **Consistent** (Sharpe 3.93)
- **Robust** (Low drawdown)
- **Profitable** (Top performer potential)

**Good luck in the competition! 🚀**

---

*Algorithm by: AI Assistant*  
*Competition: DUFS Trading Competition Round 1*  
*Date: November 19, 2025*
