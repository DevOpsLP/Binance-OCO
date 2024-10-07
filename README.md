# Binance Order Management Script

This script listens to Binance's WebSocket for order updates and manages stop-loss and take-profit orders. When one of these orders is filled, it automatically cancels the opposite order to prevent unintended positions.

## Table of Contents

- [Setting Up API Keys](#setting-up-api-keys)
- [Installation](#installation)
- [Script Overview](#script-overview)
  - [Features](#features)
  - [How It Works](#how-it-works)
- [License](#license)

## Setting Up API Keys

Before running the script, set your Binance `API_KEY` and `API_SECRET` as environment variables.

### On Linux or macOS
Open your terminal and run:

```bash
export API_KEY="your_api_key"
export API_SECRET="your_api_secret"
```

### On Windows
Open Command Prompt and run:

```cmd
set API_KEY="your_api_key"
set API_SECRET="your_api_secret"
```

**Note: Replace "your_api_key" and "your_api_secret" with your actual Binance API key and secret.**

# Installation

**Python 3.12 +**

```cmd
pip install asyncio websockets aiohttp logging
```

# Script Overview

### Features
1. WebSocket Connection: Connects to Binance's WebSocket API to receive real-time order updates.
2. Order Tracking: Monitors STOP_MARKET and TAKE_PROFIT_MARKET orders for multiple symbols.
3. Automatic Order Cancellation: When a stop-loss or take-profit order is FILLED, the script automatically cancels the opposite order.

**Note:** If an order is only PARTIALLY_FILLED, the script WILL NOT cancel the opposite order until the order is fully FILLED. Once Binance marks the remaining part of the order as _FILLED_, the cancellation of the opposite order will be triggered.
5. Listen Key Maintenance: Keeps the WebSocket listen key alive by sending a keepalive request every 30 minutes.
6. Logging: Logs important events and errors to account.log.

## How It Works

1. **Environment Variable Check**:  
   The script checks if `API_KEY` and `API_SECRET` are set. If not, it prompts you to set them and exits.

   ```python
   import os
   import sys

   API_KEY = os.getenv('API_KEY')
   API_SECRET = os.getenv('API_SECRET')

   if not API_KEY or not API_SECRET:
       print("Environment variables API_KEY and API_SECRET are not set. Please set them.")
       sys.exit(1)
   ```

2. **Obtain Listen Key:**
It requests a listen key from Binance to establish a WebSocket connection.

**Note:** Make sure you have whitelisted your IP or this will not be able to fetch your Listen Key

3. **WebSocket Connection:**

Connects to Binance's WebSocket endpoint using the listen key.

4. **Event Handling:**
Listens for `ORDER_TRADE_UPDATE` events. When such an event is received, it:
Tracks Orders: Keeps track of stop-loss and take-profit orders per symbol.
Cancels Opposite Order: If one order is filled, it cancels the opposite order to prevent conflicting positions.

```python
if order_status == 'FILLED':
    if client_order_id == symbol_orders[symbol]['stop_order_id'] and symbol_orders[symbol]['tp_order_id']:
        await cancel_order(symbol, symbol_orders[symbol]['tp_order_id'])
        symbol_orders[symbol]['tp_order_id'] = None
    elif client_order_id == symbol_orders[symbol]['tp_order_id'] and symbol_orders[symbol]['stop_order_id']:
        await cancel_order(symbol, symbol_orders[symbol]['stop_order_id'])
        symbol_orders[symbol]['stop_order_id'] = None
```

5. Listen Key Keepalive:
Sends a keepalive request every 30 minutes to keep the listen key active.

```python
async def maintain_listen_key(listen_key):
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        await keepalive_listen_key(listen_key)
```
