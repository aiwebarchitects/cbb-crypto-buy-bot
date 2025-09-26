#!/usr/bin/env python3
"""
Quick Start Script for Crypto Trading Bot

This script helps beginners set up and test the trading bot quickly.
It provides an interactive setup process and safety checks.
"""

import os
import json
import sys
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("🚀" + "="*60 + "🚀")
    print("    CRYPTO AUTO-BUY BOT - QUICK START SETUP")
    print("🚀" + "="*60 + "🚀")
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. You have:", sys.version)
        print("Please install Python 3.8 or newer from https://python.org")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'requests', 'pandas', 'numpy', 'eth_account'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} missing")
    
    if missing_packages:
        print(f"\n🔧 Installing missing packages...")
        print("Run this command:")
        print(f"pip install -r requirements.txt")
        return False
    
    return True

def check_config_file():
    """Check if config file exists and is properly configured"""
    config_path = Path("executer/config.json")
    
    if not config_path.exists():
        print("❌ Config file not found: executer/config.json")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        secret_key = config.get('secret_key', '')
        account_address = config.get('account_address', '')
        
        if not secret_key or secret_key == "YOUR_PRIVATE_KEY_HERE":
            print("❌ Private key not configured in config.json")
            return False
        
        if not account_address or account_address == "YOUR_ACCOUNT_ADDRESS_HERE":
            print("❌ Account address not configured in config.json")
            return False
        
        if not secret_key.startswith('0x') or len(secret_key) != 66:
            print("❌ Invalid private key format (should start with 0x and be 66 characters)")
            return False
        
        if not account_address.startswith('0x') or len(account_address) != 42:
            print("❌ Invalid account address format (should start with 0x and be 42 characters)")
            return False
        
        print("✅ Config file properly configured")
        return True
        
    except json.JSONDecodeError:
        print("❌ Config file is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False

def check_testnet_mode():
    """Check if bot is in testnet mode"""
    try:
        with open('start_trading.py', 'r') as f:
            content = f.read()
        
        if 'USE_TESTNET = True' in content:
            print("✅ Bot is in TESTNET mode (safe for testing)")
            return True
        elif 'USE_TESTNET = False' in content:
            print("⚠️  Bot is in MAINNET mode (REAL MONEY!)")
            return False
        else:
            print("❌ Cannot determine testnet/mainnet mode")
            return False
            
    except Exception as e:
        print(f"❌ Error checking testnet mode: {e}")
        return False

def run_price_test():
    """Test the price analysis functionality"""
    print("\n🧪 Testing price analysis...")
    try:
        # Import and test the price analyzer
        sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("low_price_analyzer", "data/24h_low_average_price_getter.py")
        low_price_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(low_price_module)
        LowPriceAnalyzer = low_price_module.LowPriceAnalyzer
        
        analyzer = LowPriceAnalyzer(range_percentage=0.15)
        
        # Test with one coin
        print("📊 Testing PUMP analysis...")
        analysis = analyzer.get_current_analysis('PUMP')
        
        if analysis:
            print(f"✅ Price analysis working!")
            print(f"   Current Price: ${analysis['current_price']:.4f}")
            print(f"   24h Low: ${analysis['24h_low']:.4f}")
            print(f"   Buy Signal: {'🟢 YES' if analysis['buy_signal'] else '⚪ NO'}")
            return True
        else:
            print("❌ Price analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Price analysis test failed: {e}")
        return False

def interactive_setup():
    """Interactive setup process"""
    print("\n🔧 INTERACTIVE SETUP")
    print("-" * 40)
    
    # Check if user has Hyperliquid account
    print("\n1️⃣ Do you have a Hyperliquid account?")
    print("   If NO: Go to https://app.hyperliquid.xyz/join/BONUS500")
    response = input("   Enter 'y' if you have an account: ").lower()
    
    if response != 'y':
        print("\n🔗 Please create your account first:")
        print("   1. Go to: https://app.hyperliquid.xyz/join/BONUS500")
        print("   2. Connect your MetaMask wallet")
        print("   3. Get your API keys")
        print("   4. Come back and run this script again")
        return False
    
    # Check if config is set up
    print("\n2️⃣ Have you configured your API keys in executer/config.json?")
    response = input("   Enter 'y' if configured: ").lower()
    
    if response != 'y':
        print("\n⚙️ Configuration needed:")
        print("   1. Open: executer/config.json")
        print("   2. Replace YOUR_PRIVATE_KEY_HERE with your actual private key")
        print("   3. Replace YOUR_ACCOUNT_ADDRESS_HERE with your actual address")
        print("   4. Save the file")
        print("   5. Run this script again")
        return False
    
    # Ask about testnet vs mainnet
    print("\n3️⃣ Do you want to test with fake money first? (RECOMMENDED)")
    response = input("   Enter 'y' for TestNet (safe), 'n' for MainNet (real money): ").lower()
    
    if response == 'y':
        # Set testnet mode
        try:
            with open('start_trading.py', 'r') as f:
                content = f.read()
            
            content = content.replace('USE_TESTNET = False', 'USE_TESTNET = True')
            
            with open('start_trading.py', 'w') as f:
                f.write(content)
            
            print("✅ Bot set to TESTNET mode (safe testing)")
        except Exception as e:
            print(f"❌ Error setting testnet mode: {e}")
            return False
    else:
        print("⚠️  MAINNET mode selected - REAL MONEY WILL BE USED!")
        confirm = input("   Type 'I UNDERSTAND' to confirm: ")
        if confirm != 'I UNDERSTAND':
            print("❌ Setup cancelled for safety")
            return False
    
    return True

def main():
    """Main setup function"""
    print_banner()
    
    print("🔍 SYSTEM CHECK")
    print("-" * 40)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Install dependencies first:")
        print("   pip install -r requirements.txt")
        return
    
    # Check config file
    config_ok = check_config_file()
    
    # Check testnet mode
    testnet_mode = check_testnet_mode()
    
    print("\n" + "="*60)
    
    if not config_ok:
        print("⚠️  CONFIGURATION NEEDED")
        if not interactive_setup():
            return
    
    # Run price test
    if not run_price_test():
        print("\n❌ Price analysis test failed. Check your internet connection.")
        return
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    if testnet_mode or 'USE_TESTNET = True' in open('start_trading.py').read():
        print("✅ Bot is ready for TESTNET trading (safe)")
        print("\n🚀 To start the bot:")
        print("   python start_trading.py")
        print("\n📊 To test price analysis only:")
        print("   python data/24h_low_average_price_getter.py")
    else:
        print("⚠️  Bot is ready for MAINNET trading (REAL MONEY)")
        print("\n🚨 FINAL WARNING:")
        print("   - This will use REAL MONEY")
        print("   - Start with small amounts")
        print("   - Monitor the bot regularly")
        print("   - You can lose money")
        print("\n🚀 To start the bot:")
        print("   python start_trading.py")
    
    print("\n📚 For detailed instructions, see:")
    print("   - README.md (overview)")
    print("   - SETUP_GUIDE.md (step-by-step)")
    
    print("\n🔗 Need help? Create account at:")
    print("   https://app.hyperliquid.xyz/join/BONUS500")

if __name__ == "__main__":
    main()
