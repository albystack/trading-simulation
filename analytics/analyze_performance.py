"""
Performance analysis tool to understand strategy behavior
Run this after backtesting to get detailed insights
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import sys

def analyze_performance(csv_path="backtest_results.csv"):
    """Analyze strategy performance from saved results"""
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: {csv_path} not found. Run backtest first!")
        return
    
    print("="*60)
    print("STRATEGY PERFORMANCE ANALYSIS")
    print("="*60)
    
    # Overall PnL
    final_pnl = df['PnL'].iloc[-1]
    max_pnl = df['PnL'].max()
    min_pnl = df['PnL'].min()
    
    print(f"\n📊 OVERALL METRICS:")
    print(f"  Final PnL: {final_pnl:,.2f}")
    print(f"  Max PnL: {max_pnl:,.2f}")
    print(f"  Min PnL (Drawdown): {min_pnl:,.2f}")
    print(f"  PnL Range: {max_pnl - min_pnl:,.2f}")
    
    # Sharpe-like metric
    pnl_changes = df['PnL'].diff().dropna()
    if len(pnl_changes) > 0 and pnl_changes.std() > 0:
        sharpe = pnl_changes.mean() / pnl_changes.std() * np.sqrt(len(pnl_changes))
        print(f"  Sharpe Ratio: {sharpe:.2f}")
    
    # Per-product analysis
    print(f"\n📈 PER-PRODUCT ANALYSIS:")
    products = [col.replace('_quantity', '') for col in df.columns if '_quantity' in col]
    
    for product in products:
        qty_col = f"{product}_quantity"
        if qty_col in df.columns:
            max_pos = df[qty_col].max()
            min_pos = df[qty_col].min()
            avg_pos = df[qty_col].abs().mean()
            final_pos = df[qty_col].iloc[-1]
            
            print(f"\n  {product}:")
            print(f"    Final Position: {final_pos}")
            print(f"    Max Long: {max_pos}, Max Short: {min_pos}")
            print(f"    Avg Abs Position: {avg_pos:.2f}")
            
            # Trading activity
            position_changes = df[qty_col].diff().abs().sum()
            print(f"    Total Volume Traded: {position_changes:.0f}")
    
    # Time series analysis
    print(f"\n📉 DRAWDOWN ANALYSIS:")
    running_max = df['PnL'].cummax()
    drawdown = df['PnL'] - running_max
    max_drawdown = drawdown.min()
    
    print(f"  Max Drawdown: {max_drawdown:,.2f}")
    
    if max_drawdown < 0:
        drawdown_periods = (drawdown < 0).astype(int)
        if drawdown_periods.sum() > 0:
            longest_dd = drawdown_periods.groupby((drawdown_periods != drawdown_periods.shift()).cumsum()).sum().max()
            print(f"  Longest Drawdown Period: {longest_dd} ticks")
    
    # PnL progression
    print(f"\n⏱️  PNL PROGRESSION:")
    quartiles = [int(len(df) * q) for q in [0.25, 0.5, 0.75, 1.0]]
    for i, q_idx in enumerate(quartiles):
        if q_idx < len(df):
            pnl_at_q = df['PnL'].iloc[q_idx]
            print(f"  After {['25%', '50%', '75%', '100%'][i]}: {pnl_at_q:,.2f}")
    
    # Win rate analysis
    print(f"\n🎯 WIN RATE:")
    winning_ticks = (pnl_changes > 0).sum()
    losing_ticks = (pnl_changes < 0).sum()
    total_ticks = len(pnl_changes)
    
    if total_ticks > 0:
        win_rate = winning_ticks / total_ticks * 100
        print(f"  Winning Ticks: {winning_ticks}/{total_ticks} ({win_rate:.1f}%)")
        print(f"  Avg Win: {pnl_changes[pnl_changes > 0].mean():.2f}")
        print(f"  Avg Loss: {pnl_changes[pnl_changes < 0].mean():.2f}")
        
        if losing_ticks > 0:
            profit_factor = abs(pnl_changes[pnl_changes > 0].sum() / pnl_changes[pnl_changes < 0].sum())
            print(f"  Profit Factor: {profit_factor:.2f}")
    
    # Create visualization
    create_detailed_plots(df, products)
    
    print(f"\n✅ Analysis complete! Check 'performance_analysis.png' for charts.")
    print("="*60)

def create_detailed_plots(df, products):
    """Create detailed performance visualization"""
    
    fig = plt.figure(figsize=(16, 12))
    
    # 1. PnL over time
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(df.index, df['PnL'], linewidth=2, color='darkgreen')
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax1.set_title('PnL Over Time', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Tick')
    ax1.set_ylabel('PnL')
    ax1.grid(True, alpha=0.3)
    
    # 2. Positions over time
    ax2 = plt.subplot(3, 2, 2)
    for product in products:
        qty_col = f"{product}_quantity"
        if qty_col in df.columns:
            ax2.plot(df.index, df[qty_col], label=product, alpha=0.7)
    ax2.set_title('Positions Over Time', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Tick')
    ax2.set_ylabel('Position')
    ax2.legend(loc='best', fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # 3. PnL distribution
    ax3 = plt.subplot(3, 2, 3)
    pnl_changes = df['PnL'].diff().dropna()
    ax3.hist(pnl_changes, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
    ax3.set_title('PnL Change Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('PnL Change per Tick')
    ax3.set_ylabel('Frequency')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Cumulative returns
    ax4 = plt.subplot(3, 2, 4)
    cumulative_returns = (df['PnL'] / df['PnL'].iloc[0] * 100) if df['PnL'].iloc[0] != 0 else df['PnL']
    ax4.plot(df.index, cumulative_returns, linewidth=2, color='purple')
    ax4.set_title('Cumulative Returns (%)', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Tick')
    ax4.set_ylabel('Return %')
    ax4.grid(True, alpha=0.3)
    
    # 5. Drawdown
    ax5 = plt.subplot(3, 2, 5)
    running_max = df['PnL'].cummax()
    drawdown = df['PnL'] - running_max
    ax5.fill_between(df.index, drawdown, 0, color='red', alpha=0.3)
    ax5.plot(df.index, drawdown, color='darkred', linewidth=1)
    ax5.set_title('Drawdown', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Tick')
    ax5.set_ylabel('Drawdown')
    ax5.grid(True, alpha=0.3)
    
    # 6. Rolling Sharpe
    ax6 = plt.subplot(3, 2, 6)
    window = 50
    rolling_returns = df['PnL'].diff()
    rolling_sharpe = (rolling_returns.rolling(window).mean() / 
                      rolling_returns.rolling(window).std() * np.sqrt(window))
    ax6.plot(df.index, rolling_sharpe, color='orange', linewidth=2)
    ax6.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax6.set_title(f'Rolling Sharpe ({window} ticks)', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Tick')
    ax6.set_ylabel('Sharpe Ratio')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('performance_analysis.png', dpi=150, bbox_inches='tight')
    print("\n📊 Charts saved to 'performance_analysis.png'")

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "backtest_results.csv"
    analyze_performance(csv_file)
