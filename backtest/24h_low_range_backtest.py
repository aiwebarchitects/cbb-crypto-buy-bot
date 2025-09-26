# 24-Hour Low Range Backtest - Buy at 24h Low Range Strategy

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

def fetch_historical_data(symbol, interval='1m', limit=1440):
    """
    Fetch historical price data from Binance API
    1440 candles = 24 hours of 1-minute data
    """
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    time.sleep(1)  # Add delay to avoid API rate limiting
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                         'close_time', 'quote_asset_volume', 'number_of_trades',
                                         'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert price columns to float
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return df
    else:
        print(f"Error fetching data for {symbol}: {response.text}")
        return None

def calculate_24h_low_range(data, window=1440, range_percentage=2.0):
    """
    Calculate 24-hour low and the buy range
    window: number of periods to look back (1440 = 24 hours of 1-minute data)
    range_percentage: percentage above 24h low to consider as buy range
    """
    # Calculate rolling 24-hour low
    data['24h_low'] = data['low'].rolling(window=window, min_periods=1).min()
    
    # Calculate buy range (24h low + range_percentage)
    data['buy_range_upper'] = data['24h_low'] * (1 + range_percentage / 100)
    
    # Flag when current price is in buy range
    data['in_buy_range'] = (data['close'] >= data['24h_low']) & (data['close'] <= data['buy_range_upper'])
    
    return data

def backtest_24h_low_strategy(coin_data, coin_name, range_percentage=2.0, position_size_usd=1000, take_profit_pct=5.0, stop_loss_pct=3.0):
    """
    Backtest 24h low range strategy: Buy when price is within range of 24h low
    """
    # Calculate 24h low and buy range
    coin_data = calculate_24h_low_range(coin_data, window=1440, range_percentage=range_percentage)
    
    # Initialize trading variables
    position = 0  # 0 = no position, 1 = long position
    entry_price = 0
    coins_owned = 0
    trades = []
    portfolio_value = position_size_usd  # Starting with $1,000 per coin
    last_check_minute = 0  # Track minutes to simulate 60-second checks
    
    # Analytics tracking
    all_24h_lows = []
    entry_prices = []
    buy_opportunities = []
    price_stats = {
        'min_price': float('inf'),
        'max_price': 0,
        'avg_price': 0,
        'min_24h_low': float('inf'),
        'max_24h_low': 0,
        'avg_24h_low': 0
    }
    
    print(f"\n=== {coin_name} 24h Low Range Backtest ===")
    print(f"Strategy: Buy when price is within {range_percentage}% of 24h low")
    print(f"Take Profit: {take_profit_pct}% | Stop Loss: {stop_loss_pct}%")
    print(f"Starting Portfolio: ${portfolio_value:,.2f}")
    print("\n--- Trade Log ---")
    
    trade_count = 0
    
    for i, row in coin_data.iterrows():
        current_price = row['close']
        current_24h_low = row['24h_low']
        buy_range_upper = row['buy_range_upper']
        in_buy_range = row['in_buy_range']
        timestamp = row['timestamp']
        current_minute = timestamp.minute
        
        # Skip if not enough data for 24h calculation
        if pd.isna(current_24h_low):
            continue
        
        # Collect analytics data
        all_24h_lows.append(current_24h_low)
        price_stats['min_price'] = min(price_stats['min_price'], current_price)
        price_stats['max_price'] = max(price_stats['max_price'], current_price)
        price_stats['min_24h_low'] = min(price_stats['min_24h_low'], current_24h_low)
        price_stats['max_24h_low'] = max(price_stats['max_24h_low'], current_24h_low)
        
        # Track buy opportunities
        if in_buy_range:
            distance_from_low = ((current_price - current_24h_low) / current_24h_low) * 100
            buy_opportunities.append({
                'timestamp': timestamp,
                'price': current_price,
                '24h_low': current_24h_low,
                'distance_pct': distance_from_low,
                'range_upper': buy_range_upper
            })
        
        # Simulate checking every 60 seconds (every minute)
        if current_minute != last_check_minute:
            last_check_minute = current_minute
            
            # Buy signal: Price is in buy range and no current position
            if in_buy_range and position == 0:
                position = 1
                entry_price = current_price
                coins_owned = portfolio_value / current_price
                trade_count += 1
                entry_prices.append(entry_price)
                
                distance_from_low = ((current_price - current_24h_low) / current_24h_low) * 100
                print(f"BUY  #{trade_count:2d} | {timestamp} | Price: ${current_price:>8.4f} | 24h Low: ${current_24h_low:>8.4f} | Distance: {distance_from_low:>5.2f}% | Coins: {coins_owned:>8.6f}")
                
            # Exit conditions when holding position
            elif position == 1:
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Take profit condition
                if profit_pct >= take_profit_pct:
                    position = 0
                    exit_price = current_price
                    portfolio_value = coins_owned * current_price
                    profit_loss = portfolio_value - (coins_owned * entry_price)
                    
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit_loss': profit_loss,
                        'profit_pct': profit_pct,
                        'entry_time': timestamp,
                        'exit_time': timestamp,
                        'coins_traded': coins_owned,
                        'exit_reason': 'TAKE_PROFIT'
                    })
                    
                    print(f"SELL #{trade_count:2d} | {timestamp} | Price: ${current_price:>8.4f} | P&L: ${profit_loss:>8.2f} ({profit_pct:>+6.2f}%) | TAKE PROFIT")
                    coins_owned = 0
                    
                # Stop loss condition
                elif profit_pct <= -stop_loss_pct:
                    position = 0
                    exit_price = current_price
                    portfolio_value = coins_owned * current_price
                    profit_loss = portfolio_value - (coins_owned * entry_price)
                    
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit_loss': profit_loss,
                        'profit_pct': profit_pct,
                        'entry_time': timestamp,
                        'exit_time': timestamp,
                        'coins_traded': coins_owned,
                        'exit_reason': 'STOP_LOSS'
                    })
                    
                    print(f"SELL #{trade_count:2d} | {timestamp} | Price: ${current_price:>8.4f} | P&L: ${profit_loss:>8.2f} ({profit_pct:>+6.2f}%) | STOP LOSS")
                    coins_owned = 0
    
    # If still holding position at the end
    if position == 1:
        final_price = coin_data.iloc[-1]['close']
        final_value = coins_owned * final_price
        unrealized_pnl = final_value - (coins_owned * entry_price)
        unrealized_pct = ((final_price - entry_price) / entry_price) * 100
        portfolio_value = final_value
        print(f"\nStill holding position - Unrealized P&L: ${unrealized_pnl:,.2f} ({unrealized_pct:+.2f}%)")
    
    # Calculate final analytics
    price_stats['avg_price'] = coin_data['close'].mean()
    price_stats['avg_24h_low'] = np.mean(all_24h_lows) if all_24h_lows else 0
    
    # Summary
    print(f"\n--- {coin_name} Summary ---")
    print(f"Completed Trades: {len(trades)}")
    print(f"Final Portfolio Value: ${portfolio_value:,.2f}")
    total_return = portfolio_value - position_size_usd
    total_return_pct = (total_return / position_size_usd) * 100
    print(f"Total Return: ${total_return:,.2f} ({total_return_pct:+.2f}%)")
    
    if len(trades) > 0:
        winning_trades = len([t for t in trades if t['profit_loss'] > 0])
        losing_trades = len([t for t in trades if t['profit_loss'] < 0])
        win_rate = (winning_trades / len(trades)) * 100
        avg_profit = sum(t['profit_loss'] for t in trades) / len(trades)
        
        take_profit_exits = len([t for t in trades if t['exit_reason'] == 'TAKE_PROFIT'])
        stop_loss_exits = len([t for t in trades if t['exit_reason'] == 'STOP_LOSS'])
        
        print(f"Win Rate: {winning_trades}/{len(trades)} ({win_rate:.1f}%)")
        print(f"Average Profit per Trade: ${avg_profit:.2f}")
        print(f"Take Profit Exits: {take_profit_exits}")
        print(f"Stop Loss Exits: {stop_loss_exits}")
        
        if winning_trades > 0:
            avg_win = sum(t['profit_loss'] for t in trades if t['profit_loss'] > 0) / winning_trades
            print(f"Average Win: ${avg_win:.2f}")
        if losing_trades > 0:
            avg_loss = sum(t['profit_loss'] for t in trades if t['profit_loss'] < 0) / losing_trades
            print(f"Average Loss: ${avg_loss:.2f}")
    
    # Detailed Analytics
    print(f"\n--- {coin_name} Detailed Analytics ---")
    print(f"PRICE STATISTICS:")
    print(f"  Price Range: ${price_stats['min_price']:,.2f} - ${price_stats['max_price']:,.2f}")
    print(f"  Average Price: ${price_stats['avg_price']:,.2f}")
    print(f"  Price Volatility: {((price_stats['max_price'] - price_stats['min_price']) / price_stats['avg_price'] * 100):.2f}%")
    
    print(f"\n24H LOW STATISTICS:")
    print(f"  24h Low Range: ${price_stats['min_24h_low']:,.2f} - ${price_stats['max_24h_low']:,.2f}")
    print(f"  Average 24h Low: ${price_stats['avg_24h_low']:,.2f}")
    print(f"  24h Low Volatility: {((price_stats['max_24h_low'] - price_stats['min_24h_low']) / price_stats['avg_24h_low'] * 100):.2f}%")
    
    print(f"\nBUY OPPORTUNITIES:")
    print(f"  Total Buy Opportunities: {len(buy_opportunities)}")
    print(f"  Opportunities Taken: {len(entry_prices)}")
    print(f"  Opportunity Conversion Rate: {(len(entry_prices) / len(buy_opportunities) * 100) if buy_opportunities else 0:.1f}%")
    
    if entry_prices:
        print(f"\nENTRY PRICE ANALYSIS:")
        print(f"  Average Entry Price: ${np.mean(entry_prices):,.2f}")
        print(f"  Entry Price Range: ${min(entry_prices):,.2f} - ${max(entry_prices):,.2f}")
        
        # Calculate average distance from 24h low for entries
        entry_distances = []
        for i, entry in enumerate(entry_prices):
            # Find corresponding 24h low for this entry
            for opp in buy_opportunities:
                if abs(opp['price'] - entry) < 0.01:  # Match entry price
                    entry_distances.append(opp['distance_pct'])
                    break
        
        if entry_distances:
            print(f"  Average Distance from 24h Low: {np.mean(entry_distances):.2f}%")
            print(f"  Distance Range: {min(entry_distances):.2f}% - {max(entry_distances):.2f}%")
    
    if buy_opportunities:
        distances = [opp['distance_pct'] for opp in buy_opportunities]
        print(f"\nBUY RANGE ANALYSIS:")
        print(f"  Average Distance from 24h Low (all opportunities): {np.mean(distances):.2f}%")
        print(f"  Distance Range: {min(distances):.2f}% - {max(distances):.2f}%")
        
        # Show first few and last few opportunities
        print(f"\nFIRST 3 BUY OPPORTUNITIES:")
        for i, opp in enumerate(buy_opportunities[:3]):
            print(f"    {i+1}. {opp['timestamp']} | Price: ${opp['price']:,.2f} | 24h Low: ${opp['24h_low']:,.2f} | Distance: {opp['distance_pct']:.2f}%")
        
        if len(buy_opportunities) > 3:
            print(f"\nLAST 3 BUY OPPORTUNITIES:")
            for i, opp in enumerate(buy_opportunities[-3:]):
                print(f"    {len(buy_opportunities)-2+i}. {opp['timestamp']} | Price: ${opp['price']:,.2f} | 24h Low: ${opp['24h_low']:,.2f} | Distance: {opp['distance_pct']:.2f}%")
    
    return trades, portfolio_value, coin_name, len(trades), {
        'price_stats': price_stats,
        'buy_opportunities': len(buy_opportunities),
        'entry_prices': entry_prices,
        'buy_opportunities_data': buy_opportunities
    }

def main():
    print("=" * 100)
    print("24-HOUR LOW RANGE BACKTEST")
    print("Strategy: Buy when price is within range of 24-hour low")
    print("Timeframe: 1-minute candles over 24 hours (checking every 60 seconds)")
    print("Position Size: $1,000 per coin")
    print("Coins: Top 9 by Market Cap")
    print("=" * 100)
    
    # Strategy parameters
    range_percentage = 0.25  # Buy within 0.25% of 24h low
    take_profit_pct = 5.0   # Take profit at 5%
    stop_loss_pct = 3.0     # Stop loss at 3%
    
    print(f"Range Percentage: {range_percentage}%")
    print(f"Take Profit: {take_profit_pct}%")
    print(f"Stop Loss: {stop_loss_pct}%")
    print("=" * 100)
    
    # Define coins to test (testing only BTC to avoid API rate limiting)
    coins = {
        'BTC': 'BTCUSDT'
    }
    
    all_results = []
    total_portfolio = 0
    total_starting = len(coins) * 1000  # $1k per coin
    total_trades = 0
    
    # Test each coin
    for coin_name, symbol in coins.items():
        print(f"\nFetching 1-minute data for {coin_name}...")
        coin_data = fetch_historical_data(symbol, interval="1m", limit=1440)  # 24 hours
        
        if coin_data is not None:
            trades, final_value, name, num_trades, analytics = backtest_24h_low_strategy(
                coin_data, coin_name, 
                range_percentage=range_percentage,
                position_size_usd=1000,
                take_profit_pct=take_profit_pct,
                stop_loss_pct=stop_loss_pct
            )
            all_results.append({
                'coin': name,
                'trades': num_trades,
                'final_value': final_value,
                'return_pct': ((final_value - 1000) / 1000) * 100,
                'return_usd': final_value - 1000
            })
            total_portfolio += final_value
            total_trades += num_trades
        else:
            print(f"Failed to fetch data for {coin_name}")
            all_results.append({
                'coin': coin_name,
                'trades': 0,
                'final_value': 1000,
                'return_pct': 0,
                'return_usd': 0
            })
            total_portfolio += 1000
    
    # Overall summary
    print("\n" + "=" * 100)
    print("OVERALL PORTFOLIO SUMMARY")
    print("=" * 100)
    print(f"{'Coin':<6} {'Trades':<8} {'Final Value':<15} {'Return %':<12} {'Return $':<12}")
    print("-" * 100)
    
    for result in all_results:
        print(f"{result['coin']:<6} {result['trades']:<8} ${result['final_value']:>12,.2f} "
              f"{result['return_pct']:>10.2f}% ${result['return_usd']:>10.2f}")
    
    print("-" * 100)
    total_return_pct = ((total_portfolio - total_starting) / total_starting) * 100
    total_return_usd = total_portfolio - total_starting
    
    print(f"{'TOTAL':<6} {total_trades:<8} ${total_portfolio:>12,.2f} "
          f"{total_return_pct:>10.2f}% ${total_return_usd:>10.2f}")
    print("=" * 100)
    
    print(f"\nBACKTEST RESULTS:")
    print(f"Starting Portfolio: ${total_starting:,.2f}")
    print(f"Final Portfolio: ${total_portfolio:,.2f}")
    print(f"Total Return: ${total_return_usd:,.2f} ({total_return_pct:+.2f}%)")
    print(f"Total Trades: {total_trades}")
    print(f"Average Trades per Coin: {total_trades / len(coins):.1f}")
    
    # Strategy insights
    profitable_coins = len([r for r in all_results if r['return_pct'] > 0])
    active_coins = len([r for r in all_results if r['trades'] > 0])
    print(f"\nSTRATEGY INSIGHTS:")
    print(f"Active Coins: {active_coins}/{len(coins)} ({active_coins/len(coins)*100:.1f}%)")
    print(f"Profitable Coins: {profitable_coins}/{len(coins)} ({profitable_coins/len(coins)*100:.1f}%)")
    
    if total_trades > 0:
        avg_return_per_trade = total_return_usd / total_trades
        print(f"Average Return per Trade: ${avg_return_per_trade:.2f}")
    
    print(f"\nSTRATEGY PARAMETERS TESTED:")
    print(f"Range Percentage: {range_percentage}%")
    print(f"Take Profit: {take_profit_pct}%")
    print(f"Stop Loss: {stop_loss_pct}%")
    print(f"Check Frequency: Every 60 seconds")

if __name__ == "__main__":
    main()
