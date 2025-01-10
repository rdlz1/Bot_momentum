import os
import time
from binance.client import Client
from dotenv import load_dotenv
from decimal import Decimal, ROUND_DOWN
import math

# Load API keys from .env file
load_dotenv('.env')

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Initialize Binance client
client = Client(API_KEY, API_SECRET)

def get_wallet_balance():
    """Generator that yields assets with positive free balance."""
    try:
        # Get account information
        account_info = client.get_account()
        balances = account_info['balances']

        for balance in balances:
            free_amount = float(balance['free'])
            if free_amount > 0:
                yield {
                    'asset': balance['asset'],
                    'free': free_amount,
                    'locked': float(balance['locked'])
                }
    except Exception as e:
        print(f"Error fetching wallet balance: {e}")

def sell_token(symbol, quantity):
    try:
        # Place a market sell order
        order = client.create_order(
            symbol=symbol,
            side='SELL',
            type='MARKET',
            quantity=quantity
        )
        print(f"Sell order successful for {symbol}! Order ID: {order['orderId']}")
    except Exception as e:
        print(f"An error occurred while selling {symbol}: {e}")

def get_lot_size(symbol):
    """Get minimum quantity and step size for a symbol."""
    try:
        exchange_info = client.get_symbol_info(symbol)
        if exchange_info is None:
            print(f"Symbol info not found for {symbol}")
            return None, None
        for f in exchange_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                min_qty = float(f['minQty'])
                step_size = float(f['stepSize'])
                return min_qty, step_size
    except Exception as e:
        print(f"Error fetching lot size for {symbol}: {e}")
    return None, None

def adjust_to_step_size(quantity, step_size):
    """Adjust quantity to comply with step size."""
    step_size_decimal = Decimal(str(step_size))
    quantity_decimal = Decimal(str(quantity))
    # Round down to the nearest multiple of step_size
    adjusted_qty = (quantity_decimal // step_size_decimal) * step_size_decimal
    return float(adjusted_qty)

def execute_dust_transfer(assets):
    """Execute dust transfer for given assets."""
    try:
        if not assets:
            print("No assets to convert to BNB")
            return

        # Convert the list of assets to a comma-separated string
        assets_str = ','.join(assets)

        print(f"Converting to BNB: {assets_str}")

        # Call dust transfer with the correct parameter format
        result = client.transfer_dust(asset=assets_str)

        if 'totalServiceCharge' in result:
            print("Dust transfer completed:")
            print(f"Total BNB received: {result.get('totalTransfered', '0')} BNB")
            print(f"Service charge: {result.get('totalServiceCharge', '0')} BNB")
        else:
            print(f"Dust transfer result: {result}")
        return result
    except Exception as e:
        print(f"Error during dust transfer: {e}")
        return None

def main():
    print("=" * 30)
    print("\nSelling remaining tokens...")
    balances = get_wallet_balance()

    for balance in balances:
        asset = balance['asset']
        if asset in ['USDT', 'BNB', 'USDTUSDT']:
            continue  # Skip USDT and BNB

        # Fetch the most recent free balance
        balance_info = client.get_asset_balance(asset=asset)
        free_amount = float(balance_info['free'])
        if free_amount == 0:
            continue  # Skip if no free balance available

        symbol = f"{asset}USDT"
        min_qty, step_size = get_lot_size(symbol)
        if min_qty is None or step_size is None:
            print(f"Lot size info not found for {symbol}. Skipping...")
            continue

        # Adjust quantity to step size and precision
        quantity = adjust_to_step_size(free_amount, step_size)

        if quantity < min_qty:
            print(f"Adjusted quantity {quantity} is below minimum {min_qty} for {symbol}. Skipping...")
            continue

        if quantity > free_amount:
            print(f"Adjusted quantity {quantity} exceeds free amount {free_amount} for {symbol}. Adjusting to available balance.")
            quantity = adjust_to_step_size(free_amount - step_size, step_size)
            if quantity < min_qty:
                print(f"Quantity after adjustment {quantity} is below minimum. Skipping {symbol}.")
                continue

        print(f"Selling {quantity} of {symbol}...")
        sell_token(symbol, quantity)
        time.sleep(1)

    print("=" * 30)
    print("Converting dust to BNB...")
    balances = list(get_wallet_balance())
    dust_candidates = []

    for balance in balances:
        asset = balance['asset']
        free_amount = float(balance['free'])
        
        if asset in ['USDT', 'BNB'] or free_amount == 0:
            continue  # Skip USDT, BNB, and empty balances

        symbol = f"{asset}USDT"
        try:
            # Fetch the current price for the symbol
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            free_usdt = free_amount * price

            # If the asset's total value is less than 1 USDT, consider it dust
            if free_usdt < 1:
                dust_candidates.append(asset)
        except Exception as e:
            print(f"Could not get price for {symbol}: {e}")
            continue  # Skip to the next asset if there's an error

    # Convert all dust assets to BNB at once
    if dust_candidates:
        execute_dust_transfer(dust_candidates)
        time.sleep(5)  # Wait for dust transfer to complete
    else:
        print("No assets to convert to BNB")

if __name__ == "__main__":
    main()