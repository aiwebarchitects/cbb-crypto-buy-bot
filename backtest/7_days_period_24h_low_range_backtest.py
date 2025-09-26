# 7 Days Period - 24-Hour Low Range Backtest - Buy at 24h Low Range Strategy
# this Backtest is Testing Only Bitcoin

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

def fetch_historical_data(symbol, interval='1m', limit=10080):
    """
    Fetch historical price data from Binance API
    10080 candles = 7 days of 1-minute data (7 * 24 * 60)
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

def backtest_24h_low_strategy(coin_data, coin_name, range_percentage=2.0, total_capital=1000, max_buy_amount=20, max_buys_per_day=5):
    """
    Backtest 24h low range strategy: Buy only when price is within range of 24h low
    """
    # Calculate 24h low and buy range
    coin_data = calculate_24h_low_range(coin_data, window=1440, range_percentage=range_percentage)
    
    # Initialize buy-only variables
    total_coins_owned = 0
    buys = []
    remaining_capital = total_capital
    last_check_minute = 0  # Track minutes to simulate 60-second checks
    
    # Daily buy tracking
    daily_buys = {}  # Track buys per day
    current_day = None
    
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
    
    print(f"\n=== {coin_name} 24h Low Range Buy-Only Strategy ===")
    print(f"Strategy: Buy when price is within {range_percentage}% of 24h low")
    print(f"Total Capital: ${total_capital:,.2f} | Max per Buy: ${max_buy_amount} | Max Buys/Day: {max_buys_per_day}")
    print(f"Remaining Capital: ${remaining_capital:,.2f}")
    print("\n--- Buy Log ---")
    
    buy_count = 0
    total_spent = 0
    
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
        
        # Track current day for daily buy limits
        day_key = timestamp.date()
        if day_key != current_day:
            current_day = day_key
            if day_key not in daily_buys:
                daily_buys[day_key] = 0
        
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
            
            # Buy signal: Price is in buy range, have capital, and within daily limits
            if (in_buy_range and 
                remaining_capital >= max_buy_amount and 
                daily_buys.get(day_key, 0) < max_buys_per_day):
                
                # Execute buy
                buy_amount = min(max_buy_amount, remaining_capital)
                coins_bought = buy_amount / current_price
                total_coins_owned += coins_bought
                remaining_capital -= buy_amount
                total_spent += buy_amount
                buy_count += 1
                daily_buys[day_key] += 1
                entry_prices.append(current_price)
                
                buys.append({
                    'buy_price': current_price,
                    'buy_amount': buy_amount,
                    'coins_bought': coins_bought,
                    'buy_time': timestamp,
                    '24h_low': current_24h_low,
                    'distance_pct': distance_from_low,
                    'day': day_key
                })
                
                distance_from_low = ((current_price - current_24h_low) / current_24h_low) * 100
                print(f"BUY  #{buy_count:2d} | {timestamp} | Price: ${current_price:>8.4f} | 24h Low: ${current_24h_low:>8.4f} | Distance: {distance_from_low:>5.2f}% | Amount: ${buy_amount:>6.2f} | Coins: {coins_bought:>8.6f}")
    
    # Calculate final portfolio value
    final_price = coin_data.iloc[-1]['close']
    final_portfolio_value = remaining_capital + (total_coins_owned * final_price)
    unrealized_value = total_coins_owned * final_price
    unrealized_pnl = unrealized_value - total_spent
    unrealized_pct = (unrealized_pnl / total_spent * 100) if total_spent > 0 else 0
    
    print(f"\n--- Final Holdings ---")
    print(f"Total Coins Owned: {total_coins_owned:>8.6f}")
    print(f"Current Price: ${final_price:>8.4f}")
    print(f"Holdings Value: ${unrealized_value:,.2f}")
    print(f"Remaining Capital: ${remaining_capital:,.2f}")
    print(f"Total Spent: ${total_spent:,.2f}")
    print(f"Unrealized P&L: ${unrealized_pnl:,.2f} ({unrealized_pct:+.2f}%)")
    
    # Calculate final analytics
    price_stats['avg_price'] = coin_data['close'].mean()
    price_stats['avg_24h_low'] = np.mean(all_24h_lows) if all_24h_lows else 0
    
    # Summary
    print(f"\n--- {coin_name} Summary ---")
    print(f"Total Buys: {len(buys)}")
    print(f"Final Portfolio Value: ${final_portfolio_value:,.2f}")
    total_return = final_portfolio_value - total_capital
    total_return_pct = (total_return / total_capital) * 100
    print(f"Total Return: ${total_return:,.2f} ({total_return_pct:+.2f}%)")
    
    # Daily buy analysis
    if daily_buys:
        print(f"\nDaily Buy Summary:")
        for day, count in daily_buys.items():
            day_buys = [b for b in buys if b['day'] == day]
            day_spent = sum(b['buy_amount'] for b in day_buys)
            print(f"  {day}: {count} buys, ${day_spent:.2f} spent")
    
    if len(buys) > 0:
        avg_buy_amount = sum(b['buy_amount'] for b in buys) / len(buys)
        avg_buy_price = sum(b['buy_price'] for b in buys) / len(buys)
        
        print(f"\nBuy Statistics:")
        print(f"Average Buy Amount: ${avg_buy_amount:.2f}")
        print(f"Average Buy Price: ${avg_buy_price:.2f}")
        print(f"Capital Utilization: {(total_spent / total_capital * 100):.1f}%")
    
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
    
    return buys, final_portfolio_value, coin_name, len(buys), {
        'price_stats': price_stats,
        'buy_opportunities': len(buy_opportunities),
        'entry_prices': entry_prices,
        'buy_opportunities_data': buy_opportunities,
        'total_spent': total_spent,
        'remaining_capital': remaining_capital,
        'total_coins_owned': total_coins_owned
    }

def test_range_percentages(coin_data, coin_name, total_capital=1000, max_buy_amount=50, max_buys_per_day=10):
    """
    Test different range percentages to find the most profitable one
    """
    # Test different range percentages
    test_ranges = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    
    print(f"\n=== TESTING DIFFERENT RANGE PERCENTAGES FOR {coin_name} ===")
    print(f"Testing ranges: {test_ranges}")
    print("=" * 80)
    
    results = []
    
    for range_pct in test_ranges:
        print(f"\nTesting {range_pct}% range...")
        
        # Run backtest with current range percentage (silent mode)
        buys, final_value, name, num_buys, analytics = backtest_24h_low_strategy_silent(
            coin_data.copy(), coin_name, 
            range_percentage=range_pct,
            total_capital=total_capital,
            max_buy_amount=max_buy_amount,
            max_buys_per_day=max_buys_per_day
        )
        
        return_pct = ((final_value - total_capital) / total_capital) * 100
        
        results.append({
            'range_pct': range_pct,
            'buys': num_buys,
            'final_value': final_value,
            'return_pct': return_pct,
            'return_usd': final_value - total_capital,
            'total_spent': analytics['total_spent'],
            'remaining_capital': analytics['remaining_capital'],
            'buy_opportunities': analytics['buy_opportunities']
        })
        
        print(f"Range: {range_pct:>5.2f}% | Buys: {num_buys:>3d} | Return: {return_pct:>+7.2f}% | Final: ${final_value:>8,.2f} | Spent: ${analytics['total_spent']:>6,.2f}")
        
        # Add delay to avoid API rate limiting
        time.sleep(0.5)
    
    return results

def backtest_24h_low_strategy_silent(coin_data, coin_name, range_percentage=2.0, total_capital=1000, max_buy_amount=20, max_buys_per_day=5):
    """
    Silent version of backtest for testing multiple parameters
    """
    # Calculate 24h low and buy range
    coin_data = calculate_24h_low_range(coin_data, window=1440, range_percentage=range_percentage)
    
    # Initialize buy-only variables
    total_coins_owned = 0
    buys = []
    remaining_capital = total_capital
    last_check_minute = 0
    
    # Daily buy tracking
    daily_buys = {}
    current_day = None
    
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
    
    buy_count = 0
    total_spent = 0
    
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
        
        # Track current day for daily buy limits
        day_key = timestamp.date()
        if day_key != current_day:
            current_day = day_key
            if day_key not in daily_buys:
                daily_buys[day_key] = 0
        
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
            
            # Buy signal: Price is in buy range, have capital, and within daily limits
            if (in_buy_range and 
                remaining_capital >= max_buy_amount and 
                daily_buys.get(day_key, 0) < max_buys_per_day):
                
                # Execute buy
                buy_amount = min(max_buy_amount, remaining_capital)
                coins_bought = buy_amount / current_price
                total_coins_owned += coins_bought
                remaining_capital -= buy_amount
                total_spent += buy_amount
                buy_count += 1
                daily_buys[day_key] += 1
                entry_prices.append(current_price)
                
                buys.append({
                    'buy_price': current_price,
                    'buy_amount': buy_amount,
                    'coins_bought': coins_bought,
                    'buy_time': timestamp,
                    '24h_low': current_24h_low,
                    'distance_pct': distance_from_low,
                    'day': day_key
                })
    
    # Calculate final portfolio value
    final_price = coin_data.iloc[-1]['close']
    final_portfolio_value = remaining_capital + (total_coins_owned * final_price)
    
    # Calculate final analytics
    price_stats['avg_price'] = coin_data['close'].mean()
    price_stats['avg_24h_low'] = np.mean(all_24h_lows) if all_24h_lows else 0
    
    return buys, final_portfolio_value, coin_name, len(buys), {
        'price_stats': price_stats,
        'buy_opportunities': len(buy_opportunities),
        'entry_prices': entry_prices,
        'buy_opportunities_data': buy_opportunities,
        'total_spent': total_spent,
        'remaining_capital': remaining_capital,
        'total_coins_owned': total_coins_owned
    }

def main():
    print("=" * 100)
    print("7-DAY PERIOD - 24-HOUR LOW RANGE BUY-ONLY BACKTEST")
    print("SELF-TESTING DIFFERENT RANGE PERCENTAGES")
    print("Strategy: Buy only when price is within range of 24-hour low")
    print("Timeframe: 1-minute candles over 7 days (checking every 60 seconds)")
    print("Total Capital: $1,000 | Max per Buy: $50 | Max Buys/Day: 10")
    print("Testing: Bitcoin (BTC)")
    print("=" * 100)
    
    # Strategy parameters
    total_capital = 1000     # Total capital
    max_buy_amount = 50      # Max $50 per buy (increased to use more capital)
    max_buys_per_day = 10    # Max 10 buys per day (increased to allow more opportunities)
    
    print(f"Total Capital: ${total_capital}")
    print(f"Max Buy Amount: ${max_buy_amount}")
    print(f"Max Buys per Day: {max_buys_per_day}")
    print("=" * 100)
    
    # Define coins to test (testing only BTC to avoid API rate limiting)
    coins = {
        'BTC': 'BTCUSDT'
    }
    
    # Fetch data once to avoid multiple API calls
    for coin_name, symbol in coins.items():
        print(f"\nFetching 7-day 1-minute data for {coin_name}...")
        coin_data = fetch_historical_data(symbol, interval="1m", limit=10080)  # 7 days
        
        if coin_data is not None:
            # Test different range percentages
            test_results = test_range_percentages(
                coin_data, coin_name, 
                total_capital=total_capital,
                max_buy_amount=max_buy_amount,
                max_buys_per_day=max_buys_per_day
            )
            
            # Find best performing range
            best_result = max(test_results, key=lambda x: x['return_pct'])
            
            print(f"\n" + "=" * 100)
            print("RANGE PERCENTAGE TEST RESULTS")
            print("=" * 100)
            print(f"{'Range %':<8} {'Buys':<6} {'Return %':<10} {'Return $':<10} {'Final Value':<12} {'Spent':<8} {'Opportunities':<12}")
            print("-" * 100)
            
            for result in test_results:
                print(f"{result['range_pct']:>6.2f}% {result['buys']:>5d} {result['return_pct']:>+8.2f}% "
                      f"${result['return_usd']:>8.2f} ${result['final_value']:>10,.2f} "
                      f"${result['total_spent']:>6.2f} {result['buy_opportunities']:>10d}")
            
            print("-" * 100)
            print(f"\nBEST PERFORMING RANGE: {best_result['range_pct']}%")
            print(f"Best Return: {best_result['return_pct']:+.2f}% (${best_result['return_usd']:+.2f})")
            print(f"Total Buys: {best_result['buys']}")
            print(f"Final Portfolio Value: ${best_result['final_value']:,.2f}")
            print(f"Capital Utilization: {(best_result['total_spent'] / total_capital * 100):.1f}%")
            
            # Now run detailed backtest with best range
            print(f"\n" + "=" * 100)
            print(f"DETAILED BACKTEST WITH OPTIMAL RANGE: {best_result['range_pct']}%")
            print("=" * 100)
            
            buys, final_value, name, num_buys, analytics = backtest_24h_low_strategy(
                coin_data.copy(), coin_name, 
                range_percentage=best_result['range_pct'],
                total_capital=total_capital,
                max_buy_amount=max_buy_amount,
                max_buys_per_day=max_buys_per_day
            )
            
        else:
            print(f"Failed to fetch data for {coin_name}")

if __name__ == "__main__":
    main()
