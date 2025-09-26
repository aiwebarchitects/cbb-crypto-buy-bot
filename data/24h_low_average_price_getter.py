#!/usr/bin/env python3
"""
24h Low Average Price Getter

This module provides 24-hour low price analysis for cryptocurrency trading.
It fetches 1-minute candle data and calculates:
- Rolling 24h low prices
- Buy range based on percentage above 24h low
- Current price analysis relative to 24h low

Used by the 24h low range trading strategy.
"""

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class LowPriceAnalyzer:
    def __init__(self, range_percentage: float = 0.05):
        """
        Initialize 24h Low Price Analyzer
        
        Args:
            range_percentage: Percentage above 24h low to consider as buy range (default: 0.05%)
        """
        self.range_percentage = range_percentage
        self.base_url = "https://api.binance.com/api/v3/klines"
        self.log_callback = None
        
        # Coin mapping for different exchanges
        self.coin_mapping = {
            'PUMP': 'PUMPUSDT',
            'ENA': 'ENAUSDT',
            'XRP': 'XRPUSDT',
            'PAXG': 'PAXGUSDT'
        }

    def set_log_callback(self, callback):
        """Set logging callback function"""
        self.log_callback = callback

    def log(self, message: str):
        """Log message using callback or print"""
        if self.log_callback:
            self.log_callback(message)
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message}")

    def fetch_1m_data(self, symbol: str, limit: int = 1440) -> Optional[pd.DataFrame]:
        """
        Fetch 1-minute historical price data from Binance API
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            limit: Number of candles to fetch (1440 = 24 hours)
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            params = {
                "symbol": symbol,
                "interval": "1m",
                "limit": limit
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            time.sleep(0.1)  # Rate limiting
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Convert price columns to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                return df
            else:
                self.log(f"❌ API Error for {symbol}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log(f"❌ Error fetching data for {symbol}: {e}")
            return None

    def calculate_24h_low_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 24h low and buy range metrics
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional columns for 24h low analysis
        """
        # Calculate rolling 24-hour low (1440 minutes)
        data['24h_low'] = data['low'].rolling(window=1440, min_periods=1).min()
        
        # Calculate buy range upper limit
        data['buy_range_upper'] = data['24h_low'] * (1 + self.range_percentage / 100)
        
        # Calculate distance from 24h low
        data['distance_from_low_pct'] = ((data['close'] - data['24h_low']) / data['24h_low']) * 100
        
        # Flag when current price is in buy range
        data['in_buy_range'] = (data['close'] >= data['24h_low']) & (data['close'] <= data['buy_range_upper'])
        
        return data

    def get_current_analysis(self, coin: str) -> Optional[Dict]:
        """
        Get current 24h low analysis for a specific coin
        
        Args:
            coin: Coin symbol (e.g., 'BTC')
            
        Returns:
            Dictionary with current analysis or None if error
        """
        try:
            # Get Binance symbol
            binance_symbol = self.coin_mapping.get(coin)
            if not binance_symbol:
                self.log(f"❌ Unknown coin: {coin}")
                return None
            
            # Fetch 24h of 1-minute data
            data = self.fetch_1m_data(binance_symbol, limit=1440)
            if data is None or data.empty:
                return None
            
            # Calculate metrics
            data = self.calculate_24h_low_metrics(data)
            
            # Get latest values
            latest = data.iloc[-1]
            
            # Calculate additional statistics
            current_price = latest['close']
            low_24h = latest['24h_low']
            buy_range_upper = latest['buy_range_upper']
            distance_pct = latest['distance_from_low_pct']
            in_buy_range = latest['in_buy_range']
            
            # Calculate 24h price statistics
            price_24h_min = data['close'].min()
            price_24h_max = data['close'].max()
            price_24h_avg = data['close'].mean()
            
            # Calculate volatility
            price_volatility = ((price_24h_max - price_24h_min) / price_24h_avg) * 100
            
            # Count buy opportunities in last 24h
            buy_opportunities_24h = data['in_buy_range'].sum()
            
            analysis = {
                'coin': coin,
                'timestamp': latest['timestamp'],
                'current_price': current_price,
                '24h_low': low_24h,
                'buy_range_upper': buy_range_upper,
                'distance_from_low_pct': distance_pct,
                'in_buy_range': bool(in_buy_range),
                'buy_signal': bool(in_buy_range),  # For compatibility with trading bot
                'range_percentage': self.range_percentage,
                
                # 24h statistics
                'price_24h_min': price_24h_min,
                'price_24h_max': price_24h_max,
                'price_24h_avg': price_24h_avg,
                'price_volatility_pct': price_volatility,
                'buy_opportunities_24h': int(buy_opportunities_24h),
                
                # Signal metadata
                'signal_type': 'BUY_RANGE' if in_buy_range else 'WAIT',
                'signal_strength': 'STRONG' if distance_pct < 0.1 else 'MODERATE' if distance_pct < 0.2 else 'WEAK'
            }
            
            return analysis
            
        except Exception as e:
            self.log(f"❌ Error analyzing {coin}: {e}")
            return None

    def get_all_coin_analysis(self, coins: List[str] = None) -> List[Dict]:
        """
        Get 24h low analysis for multiple coins
        
        Args:
            coins: List of coin symbols. If None, uses default top coins
            
        Returns:
            List of analysis dictionaries
        """
        if coins is None:
            coins = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT']
        
        analyses = []
        
        for coin in coins:
            self.log(f"📊 Analyzing {coin}...")
            analysis = self.get_current_analysis(coin)
            
            if analysis:
                analyses.append(analysis)
                
                # Log analysis
                status = "🟢 BUY RANGE" if analysis['buy_signal'] else "⚪ WAIT"
                self.log(f"   {status} | Price: ${analysis['current_price']:.4f} | "
                        f"24h Low: ${analysis['24h_low']:.4f} | "
                        f"Distance: {analysis['distance_from_low_pct']:.3f}%")
            else:
                self.log(f"   ❌ Failed to analyze {coin}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.2)
        
        return analyses

    def print_detailed_analysis(self, analysis: Dict):
        """Print detailed analysis for a coin"""
        coin = analysis['coin']
        
        print(f"\n{'='*60}")
        print(f"📊 {coin} - 24h Low Range Analysis")
        print(f"{'='*60}")
        print(f"🕐 Timestamp: {analysis['timestamp']}")
        print(f"💰 Current Price: ${analysis['current_price']:.4f}")
        print(f"📉 24h Low: ${analysis['24h_low']:.4f}")
        print(f"🎯 Buy Range Upper: ${analysis['buy_range_upper']:.4f}")
        print(f"📏 Distance from Low: {analysis['distance_from_low_pct']:.3f}%")
        print(f"🎯 Range Setting: {analysis['range_percentage']:.2f}%")
        
        print(f"\n📈 24h Price Statistics:")
        print(f"   Min: ${analysis['price_24h_min']:.4f}")
        print(f"   Max: ${analysis['price_24h_max']:.4f}")
        print(f"   Avg: ${analysis['price_24h_avg']:.4f}")
        print(f"   Volatility: {analysis['price_volatility_pct']:.2f}%")
        
        print(f"\n🎯 Buy Signal Analysis:")
        signal_emoji = "🟢" if analysis['buy_signal'] else "⚪"
        print(f"   {signal_emoji} Signal: {analysis['signal_type']}")
        print(f"   💪 Strength: {analysis['signal_strength']}")
        print(f"   🔢 Buy Opportunities (24h): {analysis['buy_opportunities_24h']}")
        
        if analysis['buy_signal']:
            print(f"\n✅ BUY SIGNAL ACTIVE!")
            print(f"   Price is within {analysis['range_percentage']:.2f}% of 24h low")
            print(f"   Current distance: {analysis['distance_from_low_pct']:.3f}%")
        else:
            print(f"\n⏳ WAITING...")
            print(f"   Price is {analysis['distance_from_low_pct']:.3f}% above 24h low")
            print(f"   Need price ≤ ${analysis['buy_range_upper']:.4f} for buy signal")


def main():
    """Test the 24h Low Price Analyzer"""
    print("🔍 24h Low Average Price Getter - Test Mode")
    print("="*60)
    
    # Initialize analyzer
    analyzer = LowPriceAnalyzer(range_percentage=0.05)
    
    # Test single coin analysis
    print("\n📊 Testing BTC Analysis...")
    btc_analysis = analyzer.get_current_analysis('BTC')
    
    if btc_analysis:
        analyzer.print_detailed_analysis(btc_analysis)
    else:
        print("❌ Failed to get BTC analysis")
    
    # Test multiple coins
    print(f"\n📊 Testing Multiple Coins Analysis...")
    test_coins = ['BTC', 'ETH', 'SOL']
    analyses = analyzer.get_all_coin_analysis(test_coins)
    
    print(f"\n📋 Summary for {len(analyses)} coins:")
    buy_signals = [a for a in analyses if a['buy_signal']]
    print(f"🟢 Buy Signals: {len(buy_signals)}")
    print(f"⚪ Waiting: {len(analyses) - len(buy_signals)}")
    
    if buy_signals:
        print(f"\n🎯 Active Buy Signals:")
        for analysis in buy_signals:
            print(f"   {analysis['coin']}: ${analysis['current_price']:.4f} "
                  f"({analysis['distance_from_low_pct']:.3f}% from low)")


if __name__ == "__main__":
    main()
