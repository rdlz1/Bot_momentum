import os
from binance.client import Client
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv('/Users/desk/Python/Bot_Momentum/.env')
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Initialize Binance client
client = Client(API_KEY, API_SECRET)

def get_positive_balances(return_balances=False):
    """Fetch and display positive balances from Binance account with USDT equivalent values."""
    try:
        total_usdt_value = 0.0
        # Retrieve account information
        account_info = client.get_account()
        balances = account_info['balances']
        
        positive_balances = []
        
        print("Positive Balances with USDT Equivalent:")
        print("=" * 60)
        for balance in balances:
            asset = balance['asset']
            free_amount = float(balance['free'])
            locked_amount = float(balance['locked'])
            total_amount = free_amount + locked_amount
            if total_amount > 0:
                usdt_value = get_usdt_value(asset, total_amount)
                total_usdt_value += usdt_value
                positive_balances.append({
                    'asset': asset,
                    'amount': total_amount,
                    'usdt_value': usdt_value
                })
                print(f"{asset}: {total_amount} (~{usdt_value:.2f} USDT)")
        print(f"Total Portfolio Value: {total_usdt_value:.2f} USDT")

        if return_balances:
            return positive_balances
    except Exception as e:
        print(f"An error occurred: {e}")
        if return_balances:
            return []
        else:
            return

def get_usdt_value(asset, total_amount):
    """Get the USDT equivalent value of an asset."""
    if asset == 'USDT':
        return total_amount
    symbol = f"{asset}USDT"
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        return total_amount * price
    except Exception:
        return 0.0

if __name__ == "__main__":
    get_positive_balances()