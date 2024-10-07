import asyncio
import websockets
import json
import hmac
import hashlib
import time
import aiohttp
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='account.log', filemode='a')

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Check if environment variables are set
if not API_KEY or not API_SECRET:
    print("Environment variables API_KEY and API_SECRET are not set. Please set them as follows:\n")
    print("On Linux or macOS:\n")
    print('export API_KEY="your_api_key"')
    print('export API_SECRET="your_api_secret"\n')
    print("On Windows:\n")
    print('set API_KEY="your_api_key"')
    print('set API_SECRET="your_api_secret"\n')
    sys.exit(1)  # Exit the script with an error code

BINANCE_API_BASE_URL = "https://fapi.binance.com"

LISTEN_KEY_ENDPOINT = "/fapi/v1/listenKey"
CANCEL_ORDER_ENDPOINT = "/fapi/v1/order"

# Dictionary to track stop and take profit orders per symbol
symbol_orders = {}

def generate_signature(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

async def keepalive_listen_key(listen_key):
    url = f"{BINANCE_API_BASE_URL}{LISTEN_KEY_ENDPOINT}"
    
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers) as response:
            if response.status == 200:
                logging.info(f"Listen key {listen_key} has been extended.")
            else:
                logging.info(f"Failed to extend listen key: {response.status}")

async def cancel_order(symbol, order_id):
    url = f"{BINANCE_API_BASE_URL}{CANCEL_ORDER_ENDPOINT}"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': symbol,
        'origClientOrderId': order_id,
        'timestamp': timestamp,
    }
    
    # Sign the request
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = generate_signature(query_string, API_SECRET)
    params['signature'] = signature
    
    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{url}?{query_string}&signature={signature}", headers=headers) as response:
            if response.status == 200:
                logging.info(f"Order {order_id} canceled for symbol: {symbol}")
            else:
                logging.info(f"Failed to cancel order {order_id}: HTTP {response}")

async def listen_to_binance():
    listen_key = await get_listen_key()
    if not listen_key:
        return
    
    url = f"wss://fstream.binance.com/ws/{listen_key}"

    async with websockets.connect(url) as ws:
        logging.info("Connected to WebSocket. Listening for events...")

        while True:
            try:
                response = await ws.recv()
                event = json.loads(response)
                
                if event['e'] == 'ORDER_TRADE_UPDATE':
                    order = event['o']
                    symbol = order['s']
                    order_type = order['o']
                    order_status = order['X']
                    client_order_id = order['c']

                    logging.info(f"Received event: {event}")

                    # Initialize symbol tracking if it doesn't exist
                    if symbol not in symbol_orders:
                        symbol_orders[symbol] = {'stop_order_id': None, 'tp_order_id': None}

                    # Track STOP_MARKET and TAKE_PROFIT_MARKET orders
                    if order_type == 'STOP_MARKET' and order_status == 'NEW':
                        symbol_orders[symbol]['stop_order_id'] = client_order_id
                    elif order_type == 'TAKE_PROFIT_MARKET' and order_status == 'NEW':
                        symbol_orders[symbol]['tp_order_id'] = client_order_id

                    # Cancel the opposite order when one of them gets filled
                    if order_status == 'FILLED':
                        if client_order_id == symbol_orders[symbol]['stop_order_id'] and symbol_orders[symbol]['tp_order_id']:
                            await cancel_order(symbol, symbol_orders[symbol]['tp_order_id'])
                            symbol_orders[symbol]['tp_order_id'] = None
                        elif client_order_id == symbol_orders[symbol]['tp_order_id'] and symbol_orders[symbol]['stop_order_id']:
                            await cancel_order(symbol, symbol_orders[symbol]['stop_order_id'])
                            symbol_orders[symbol]['stop_order_id'] = None

            except websockets.ConnectionClosed as e:
                logging.info(f"Connection closed: {e}")
                break

async def get_listen_key():
    url = f"{BINANCE_API_BASE_URL}{LISTEN_KEY_ENDPOINT}"

    headers = {
        'X-MBX-APIKEY': API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['listenKey']
            else:
                logging.info(f"Failed to get listen key: {response.status}")
                return None

async def maintain_listen_key(listen_key):
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        await keepalive_listen_key(listen_key)

async def main():
    listen_key = await get_listen_key()
    if listen_key:
        asyncio.create_task(maintain_listen_key(listen_key))
        await listen_to_binance()

if __name__ == "__main__":
    asyncio.run(main())
