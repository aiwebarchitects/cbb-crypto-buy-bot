#!/usr/bin/env python3
"""
Trading Bot v0.1 - Buy the 24h Lows.

This bot implements the 24h low range buying strategy:
1. Gets 24h low analysis from 24h_low_average_price_getter.py
2. Checks existing positions for each coin
3. Executes trades:
   - Create market buy order when price is within 0.05% of 24h low
   - NO SELLING - Buy-only bot that accumulates positions

Strategy:
- Buy Signal: Price within 0.15% of 24h low
- No Selling: Buy-only accumulation strategy
- Timeframe: 1-minute candles with 24h rolling window
- Check Frequency: Every 60 seconds
- Order Type: Market orders for immediate execution
- Coins: BTC, AVAX (Hyperliquid supported)
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add executer directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'executer'))

# Import our modules
import importlib.util
spec = importlib.util.spec_from_file_location("low_price_analyzer", "data/24h_low_average_price_getter.py")
low_price_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(low_price_module)
LowPriceAnalyzer = low_price_module.LowPriceAnalyzer

import example_utils
from hyperliquid.utils import constants


class TradingBotV01:
    def __init__(self, use_testnet: bool = True):
        """
        Initialize Trading Bot v0.1
        
        Args:
            use_testnet: If True, use testnet. If False, use mainnet (DANGEROUS!)
        """
        self.use_testnet = use_testnet
        self.api_url = constants.TESTNET_API_URL if use_testnet else constants.MAINNET_API_URL
        
        # Initialize 24h low analyzer
        self.low_analyzer = LowPriceAnalyzer(range_percentage=0.15)
        self.low_analyzer.set_log_callback(self.log)
        
        # Trading configuration
        self.position_value_usd = 20.0  # $20 USD per position
        self.max_position_value_usd = 140.0  # Maximum total position value per coin
        self.check_interval = 60  # Check every 60 seconds
        
        # Initialize exchange connection
        self.address = None
        self.info = None
        self.exchange = None
        self._setup_exchange()
        
        # Coin mapping for Hyperliquid (some symbols might be different)
        self.coin_mapping = {
            'PUMP': 'PUMP',
            'ENA': 'ENA',
            'XRP': 'XRP',
            'PAXG': 'PAXG'
        }

    def _setup_exchange(self):
        """Setup exchange connection"""
        try:
            self.address, self.info, self.exchange = example_utils.setup(
                self.api_url, skip_ws=True
            )
            # CRITICAL: Always check actual API URL to determine real connection
            actual_connection = "TESTNET" if "testnet" in self.api_url.lower() else "MAINNET"
            self.log(f"🚨 CONNECTED TO: {actual_connection}")
            self.log(f"🚨 API URL: {self.api_url}")
            self.log(f"📍 Trading Address: {self.address}")
            
            if actual_connection == "MAINNET":
                self.log("🚨🚨🚨 WARNING: REAL MONEY ACCOUNT - MAINNET CONNECTION 🚨🚨🚨")
                self.log("🚨🚨🚨 ALL TRADES WILL USE REAL FUNDS 🚨🚨🚨")
            
        except Exception as e:
            self.log(f"❌ Failed to setup exchange: {e}")
            raise

    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def get_current_positions(self) -> Dict[str, Dict]:
        """
        Get current positions for all coins
        
        Returns:
            Dict mapping coin symbol to position info
        """
        try:
            user_state = self.info.user_state(self.address)
            positions = {}
            
            for position in user_state.get("assetPositions", []):
                coin = position.get("position", {}).get("coin")
                if coin in self.coin_mapping.values():
                    positions[coin] = position.get("position", {})
            
            return positions
        except Exception as e:
            self.log(f"❌ Error getting positions: {e}")
            return {}

    def has_position(self, coin: str) -> bool:
        """Check if we have an open position for a coin"""
        positions = self.get_current_positions()
        hyperliquid_coin = self.coin_mapping.get(coin, coin)
        
        if hyperliquid_coin in positions:
            position_size = float(positions[hyperliquid_coin].get("szi", "0"))
            return abs(position_size) > 0
        return False

    def get_position_info(self, coin: str) -> Optional[Dict]:
        """Get position info for a specific coin"""
        positions = self.get_current_positions()
        hyperliquid_coin = self.coin_mapping.get(coin, coin)
        return positions.get(hyperliquid_coin)

    def get_position_value_usd(self, coin: str) -> float:
        """
        Get current USD value of position for a specific coin
        
        Args:
            coin: Coin symbol (e.g., 'BTC', 'AVAX')
            
        Returns:
            Current position value in USD
        """
        try:
            hyperliquid_coin = self.coin_mapping.get(coin, coin)
            
            # Get current position
            position_info = self.get_position_info(coin)
            if not position_info:
                return 0.0
            
            position_size = float(position_info.get("szi", "0"))
            if abs(position_size) == 0:
                return 0.0
            
            # Get current market price
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(hyperliquid_coin, 0))
            
            if current_price == 0:
                return 0.0
            
            # Calculate position value
            position_value = abs(position_size) * current_price
            return position_value
            
        except Exception as e:
            self.log(f"❌ Error calculating position value for {coin}: {e}")
            return 0.0

    def can_buy_more(self, coin: str) -> tuple[bool, float, float]:
        """
        Check if we can buy more of a coin without exceeding max position value
        
        Args:
            coin: Coin symbol (e.g., 'BTC', 'AVAX')
            
        Returns:
            Tuple of (can_buy, current_value, remaining_capacity)
        """
        current_value = self.get_position_value_usd(coin)
        remaining_capacity = self.max_position_value_usd - current_value
        
        # Can buy if remaining capacity is at least equal to one trade size
        can_buy = remaining_capacity >= self.position_value_usd
        
        return can_buy, current_value, remaining_capacity

    def get_tick_size_price(self, coin: str, target_price: float) -> float:
        """Round price to valid tick size"""
        if coin == "ETH":
            return int(round(target_price))
        else:
            return round(target_price, 2)

    def create_market_buy_order(self, coin: str, analysis: Dict) -> Dict:
        """
        Create a market buy order using fixed USD value
        
        Args:
            coin: Coin symbol (e.g., 'BTC', 'ETH')
            analysis: 24h low analysis data
            
        Returns:
            Dict with order result
        """
        try:
            hyperliquid_coin = self.coin_mapping.get(coin, coin)
            
            # Get current market price from analysis
            current_price = analysis['current_price']
            
            # Get exchange metadata for proper rounding
            meta = self.info.meta()
            sz_decimals = {}
            for asset_info in meta["universe"]:
                sz_decimals[asset_info["name"]] = asset_info["szDecimals"]
            
            if hyperliquid_coin not in sz_decimals:
                return {"status": "error", "error": f"Could not find szDecimals for {hyperliquid_coin}"}
            
            # Calculate position size based on USD value
            raw_size = self.position_value_usd / current_price
            
            # Round size according to szDecimals
            size = round(raw_size, sz_decimals[hyperliquid_coin])
            
            self.log(f"📊 {coin} Market Buy Order Info:")
            self.log(f"   Current Price: ${current_price:.4f}")
            self.log(f"   24h Low: ${analysis['24h_low']:.4f}")
            self.log(f"   Distance from Low: {analysis['distance_from_low_pct']:.3f}%")
            self.log(f"   USD Value: ${self.position_value_usd}")
            self.log(f"   Size: {size:.6f} {coin}")
            
            # Place market buy order
            is_buy = True
            order_result = self.exchange.market_open(
                hyperliquid_coin, 
                is_buy, 
                size, 
                None  # No price limit for market order
            )
            
            if order_result.get("status") == "ok":
                self.log(f"✅ {coin} MARKET BUY executed successfully!")
                return {"status": "ok", "result": order_result}
            else:
                return {"status": "error", "error": f"Order failed: {order_result}"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}


    def process_coin_analysis(self, analysis: Dict) -> Dict:
        """
        Process a single coin's 24h low analysis and execute appropriate action
        
        Args:
            analysis: Analysis dictionary from LowPriceAnalyzer
            
        Returns:
            Dict with action result
        """
        coin = analysis['coin']
        has_pos = self.has_position(coin)
        can_buy_more, current_value, remaining_capacity = self.can_buy_more(coin)
        
        result = {
            'coin': coin,
            'signal': analysis['signal_type'],
            'buy_signal': analysis['buy_signal'],
            'distance_from_low': analysis['distance_from_low_pct'],
            'has_position': has_pos,
            'current_value': current_value,
            'remaining_capacity': remaining_capacity,
            'action': 'NONE',
            'success': False,
            'message': ''
        }
        
        # Buy-only bot: Only create buy orders, never sell
        # Buy if: buy signal AND can buy more (within position limit)
        if analysis['buy_signal'] and can_buy_more:
            self.log(f"🟢 {coin}: Executing market buy (Distance: {analysis['distance_from_low_pct']:.3f}%)")
            self.log(f"   💵 Current Position Value: ${current_value:.2f}")
            self.log(f"   🔄 Remaining Capacity: ${remaining_capacity:.2f}")
            order_result = self.create_market_buy_order(coin, analysis)
            
            result['action'] = 'MARKET_BUY'
            result['success'] = order_result.get('status') == 'ok'
            result['message'] = order_result.get('error', 'Market buy executed') if not result['success'] else 'Market buy executed successfully'
            
        # No action needed - various reasons
        else:
            if not analysis['buy_signal']:
                result['message'] = f"No buy signal - price {analysis['distance_from_low_pct']:.3f}% above 24h low"
            elif not can_buy_more:
                if current_value >= self.max_position_value_usd:
                    result['message'] = f"Position limit reached (${current_value:.2f}/${self.max_position_value_usd:.2f})"
                else:
                    result['message'] = f"Insufficient capacity (${remaining_capacity:.2f} < ${self.position_value_usd})"
            else:
                result['message'] = f"Waiting for buy opportunity (Value: ${current_value:.2f})"
        
        return result

    def run_trading_cycle(self) -> List[Dict]:
        """
        Run one complete trading cycle for all coins
        
        Returns:
            List of action results for each coin
        """
        self.log("🚀 Starting 24h Low Range trading cycle...")
        self.log("=" * 80)
        
        # Get coins to analyze (only those we can trade on Hyperliquid)
        coins_to_analyze = list(self.coin_mapping.keys())
        
        # Get all 24h low analyses
        analyses = self.low_analyzer.get_all_coin_analysis(coins_to_analyze)
        results = []
        
        # Process each coin
        for analysis in analyses:
            if analysis is None:
                continue
                
            result = self.process_coin_analysis(analysis)
            results.append(result)
            
            # Log the result
            action_emoji = {
                'MARKET_BUY': '🟢',
                'NONE': '⚪'
            }.get(result['action'], '⚪')
            
            status_emoji = '✅' if result['success'] or result['action'] == 'NONE' else '❌'
            
            # Enhanced logging with 24h low info
            self.log(f"{action_emoji} {status_emoji} {result['coin']}: {result['message']}")
            if analysis['buy_signal']:
                self.log(f"   📊 Price: ${analysis['current_price']:.4f} | 24h Low: ${analysis['24h_low']:.4f} | Range: 0.05%")
        
        # Summary
        actions_taken = len([r for r in results if r['action'] != 'NONE'])
        successful_actions = len([r for r in results if r['success'] and r['action'] != 'NONE'])
        buy_signals = len([r for r in results if r['buy_signal']])
        
        self.log("=" * 80)
        self.log(f"📊 Cycle Summary:")
        self.log(f"   🎯 Buy Signals: {buy_signals}")
        self.log(f"   🟢 Actions Taken: {actions_taken}")
        self.log(f"   ✅ Successful: {successful_actions}")
        self.log("🏁 Trading cycle completed")
        
        return results

    def show_portfolio_status(self):
        """Show current portfolio status"""
        self.log("📊 PORTFOLIO STATUS")
        self.log("-" * 50)
        
        try:
            # Get account info
            user_state = self.info.user_state(self.address)
            margin_summary = user_state.get("marginSummary", {})
            
            account_value = float(margin_summary.get("accountValue", "0"))
            total_pnl = float(margin_summary.get("totalPnl", "0"))
            
            self.log(f"💰 Account Value: ${account_value:.2f}")
            self.log(f"📈 Total PnL: ${total_pnl:.2f}")
            
            # Show position values and limits for each coin
            self.log("📍 Position Analysis:")
            for coin_name in self.coin_mapping.keys():
                can_buy_more, current_value, remaining_capacity = self.can_buy_more(coin_name)
                
                if current_value > 0:
                    remaining_trades = remaining_capacity / self.position_value_usd if remaining_capacity > 0 else 0
                    status = "🟢 CAN BUY" if can_buy_more else "🚫 LIMIT REACHED"
                    self.log(f"   {coin_name}: ${current_value:.2f}/${self.max_position_value_usd:.2f} | "
                            f"Remaining: ${remaining_capacity:.2f} ({remaining_trades:.1f} trades) | {status}")
                else:
                    max_trades = self.max_position_value_usd / self.position_value_usd
                    self.log(f"   {coin_name}: No position | Can buy: ${self.max_position_value_usd:.2f} ({max_trades:.1f} trades)")
                
        except Exception as e:
            self.log(f"❌ Error getting portfolio status: {e}")

    def run_continuous(self, cycle_interval: int = 60):
        """
        Run trading bot continuously
        
        Args:
            cycle_interval: Seconds between trading cycles (default: 60 seconds)
        """
        self.log(f"🤖 Trading Bot v0.1 Starting - Buy-Only Mode")
        self.log(f"⏰ Cycle Interval: {cycle_interval} seconds")
        self.log(f"🎯 Strategy: Buy within 0.05% of 24h low (Buy Only) - No Selling")
        self.log(f"💰 Position Value: ${self.position_value_usd} USD per trade")
        self.log(f"🎯 Max Position Value: ${self.max_position_value_usd} USD per coin")
        self.log("=" * 80)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                self.log(f"\n🔄 CYCLE #{cycle_count}")
                
                # Show portfolio status every 10 cycles
                if cycle_count % 10 == 1:
                    self.show_portfolio_status()
                    self.log("")
                
                # Run trading cycle
                results = self.run_trading_cycle()
                
                # Wait for next cycle
                self.log(f"⏳ Waiting {cycle_interval} seconds until next cycle...")
                time.sleep(cycle_interval)
                
        except KeyboardInterrupt:
            self.log("\n🛑 Trading bot stopped by user")
        except Exception as e:
            self.log(f"\n❌ Trading bot error: {e}")
            raise


def main():
    """Main function to run the trading bot"""
    print("🤖 Trading Bot v0.1 - 24h Low Range System")
    print("=" * 60)
    
    # Configuration
    USE_TESTNET = False  # Using mainnet for real trading
    CYCLE_INTERVAL = 60  # 60 seconds between cycles
    
    try:
        # Initialize and run bot
        bot = TradingBotV01(use_testnet=USE_TESTNET)
        
        # Show initial status
        bot.show_portfolio_status()
        
        # Run one cycle first to test
        print("\n🧪 Running test cycle...")
        bot.run_trading_cycle()
        
        # Ask if user wants to continue
        print("\n" + "=" * 60)
        response = input("Continue with continuous trading? (y/N): ")
        if response.lower() == 'y':
            bot.run_continuous(CYCLE_INTERVAL)
        else:
            print("Single cycle completed. Exiting...")
            
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")


if __name__ == "__main__":
    main()
