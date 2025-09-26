# 🔧 Complete Setup Guide for Beginners

**Step-by-step instructions to get your crypto trading bot running in 15 minutes**

## 🎯 What You'll Need

- **Computer** (Windows, Mac, or Linux)
- **Internet connection**
- **MetaMask wallet** (we'll help you set this up)
- **$100-500** to start trading
- **15 minutes** of your time

---

## 📱 Step 1: Install MetaMask Wallet

### If you don't have MetaMask:

1. **Go to [metamask.io](https://metamask.io)**
2. **Click "Download"** and install the browser extension
3. **Create a new wallet** and save your seed phrase securely
4. **Write down your seed phrase** on paper (very important!)

### If you already have MetaMask:
✅ You're ready for the next step!

---

## 🚀 Step 2: Create Your Hyperliquid Account

1. **Click here: [https://app.hyperliquid.xyz/join/BONUS500](https://app.hyperliquid.xyz/join/BONUS500)**
2. **Click "Connect Wallet"**
3. **Select MetaMask** from the options
4. **Approve the connection** in MetaMask
5. **You're now logged in!** ✅

### 💰 Deposit Funds (Optional for TestNet)

- **For TestNet**: No real money needed
- **For MainNet**: Deposit USDC to start trading
  - Click "Deposit" in Hyperliquid
  - Follow the instructions to transfer USDC

---

## 🔑 Step 3: Get Your API Keys

### 3.1 Generate API Keys

1. **In Hyperliquid, click your profile** (top right)
2. **Go to "API"** or "Settings"
3. **Click "Generate API Key"**
4. **Copy both values**:
   - **Private Key** (starts with 0x...)
   - **Account Address** (starts with 0x...)

### 3.2 Save Your Keys Safely

**⚠️ CRITICAL**: These keys control your money. Keep them secret!

Create a text file and save:
```
My Hyperliquid API Keys:
Private Key: 0x1234567890abcdef... (your actual key)
Account Address: 0x9876543210fedcba... (your actual address)
```

---

## 💻 Step 4: Install Python

### Windows:
1. **Go to [python.org](https://python.org)**
2. **Download Python 3.8+** (latest version)
3. **Run installer** and check "Add to PATH"
4. **Open Command Prompt** and type: `python --version`

### Mac:
1. **Open Terminal**
2. **Install Homebrew**: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
3. **Install Python**: `brew install python`
4. **Check version**: `python3 --version`

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3 python3-pip
python3 --version
```

---

## 📁 Step 5: Download the Bot

### Option A: Download ZIP
1. **Click "Code" → "Download ZIP"** on GitHub
2. **Extract the ZIP file** to your Desktop
3. **Open the folder** in your file explorer

### Option B: Use Git (Advanced)
```bash
git clone https://github.com/yourusername/crypto-auto-buy-bot.git
cd crypto-auto-buy-bot
```

---

## 🔧 Step 6: Install Bot Dependencies

### Windows:
1. **Open Command Prompt**
2. **Navigate to bot folder**: `cd Desktop\crypto-auto-buy-bot`
3. **Install packages**: `pip install -r requirements.txt`

### Mac/Linux:
1. **Open Terminal**
2. **Navigate to bot folder**: `cd Desktop/crypto-auto-buy-bot`
3. **Install packages**: `pip3 install -r requirements.txt`

**Wait for installation to complete** (2-3 minutes)

---

## ⚙️ Step 7: Configure the Bot

### 7.1 Open Configuration File

**Find and open**: `executer/config.json`

You can use:
- **Notepad** (Windows)
- **TextEdit** (Mac)
- **Any text editor**

### 7.2 Update Your Keys

**Replace the placeholder values**:

```json
{
    "secret_key": "YOUR_PRIVATE_KEY_FROM_STEP_3",
    "account_address": "YOUR_ACCOUNT_ADDRESS_FROM_STEP_3",
    "multi_sig": {
        "authorized_users": [
            {
                "comment": "signer 1",
                "secret_key": "",
                "account_address": ""
            }
        ]
    }
}
```

**Example** (with fake keys):
```json
{
    "secret_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "account_address": "0x9876543210fedcba9876543210fedcba98765432",
    "multi_sig": {
        "authorized_users": [
            {
                "comment": "signer 1",
                "secret_key": "",
                "account_address": ""
            }
        ]
    }
}
```

**Save the file** when done.

---

## 🧪 Step 8: Test the Bot (Safe Mode)

### 8.1 Enable TestNet Mode

**Open**: `start_trading.py`

**Find this line** (around line 200):
```python
USE_TESTNET = False
```

**Change it to**:
```python
USE_TESTNET = True
```

**Save the file**.

### 8.2 Test Price Analysis

**Run this command**:

**Windows**: `python data\24h_low_average_price_getter.py`
**Mac/Linux**: `python3 data/24h_low_average_price_getter.py`

**You should see**:
```
📊 Analyzing PUMP...
   ⚪ WAIT | Price: $0.1234 | 24h Low: $0.1200 | Distance: 2.833%
📊 Analyzing ENA...
   🟢 BUY RANGE | Price: $0.5678 | 24h Low: $0.5670 | Distance: 0.141%
```

✅ **If you see this, everything is working!**

---

## 🚀 Step 9: Run the Bot

### 9.1 Start in Test Mode

**Windows**: `python start_trading.py`
**Mac/Linux**: `python3 start_trading.py`

**You should see**:
```
🤖 Trading Bot v0.1 Starting - Buy-Only Mode
🚨 CONNECTED TO: TESTNET
⏰ Cycle Interval: 60 seconds
🎯 Strategy: Buy within 0.15% of 24h low
```

### 9.2 Monitor the Bot

The bot will:
- ✅ Check prices every 60 seconds
- ✅ Show you what it's doing
- ✅ Make test trades (no real money)

**Let it run for 10-15 minutes** to see how it works.

### 9.3 Stop the Bot

**Press**: `Ctrl+C` (Windows/Linux) or `Cmd+C` (Mac)

---

## 💰 Step 10: Switch to Real Trading (Optional)

### ⚠️ ONLY DO THIS AFTER TESTING!

### 10.1 Deposit Real Money

1. **Go to Hyperliquid**
2. **Click "Deposit"**
3. **Transfer USDC** to your account
4. **Start with $100-200** for safety

### 10.2 Enable MainNet

**In `start_trading.py`**:
```python
USE_TESTNET = False  # Real money mode!
```

### 10.3 Start Real Trading

**Run the bot again**:
```bash
python start_trading.py
```

**You should see**:
```
🚨🚨🚨 WARNING: REAL MONEY ACCOUNT - MAINNET CONNECTION 🚨🚨🚨
```

---

## 🛡️ Safety Checklist

Before running with real money:

- ✅ **Tested on TestNet** successfully
- ✅ **Understand the strategy** (buy-only, $20 per trade)
- ✅ **Have stop-loss plan** (know how to stop the bot)
- ✅ **Started with small amount** ($100-200)
- ✅ **Monitor regularly** (check every few hours)
- ✅ **Secure your keys** (never share them)

---

## 🆘 Common Problems & Solutions

### ❌ "Python not found"
**Solution**: Reinstall Python and check "Add to PATH"

### ❌ "pip not found"
**Windows**: Use `py -m pip install -r requirements.txt`
**Mac**: Use `python3 -m pip install -r requirements.txt`

### ❌ "No accountValue" error
**Solution**: 
1. Check your API keys are correct
2. Deposit funds to your Hyperliquid account
3. Make sure you're using the right account address

### ❌ "API Error" messages
**Solution**:
1. Check your internet connection
2. Verify your API keys
3. Try again in a few minutes

### ❌ Bot stops working
**Solution**:
1. Check the error message
2. Restart the bot
3. Make sure your account has funds

---

## 📞 Getting Help

1. **Read the error message** carefully
2. **Check this guide** for solutions
3. **Test on TestNet** first
4. **Start with small amounts**
5. **Join the community** for support

---

## 🎉 Congratulations!

You now have a working crypto trading bot! 

**Remember**:
- 🧪 **Always test first**
- 💰 **Start small**
- 👀 **Monitor regularly**
- 🛡️ **Trade responsibly**

**Happy trading!** 🚀

---

**Need to create your account? [Click here for Hyperliquid](https://app.hyperliquid.xyz/join/BONUS500)**
