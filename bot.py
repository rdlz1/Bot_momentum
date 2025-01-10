import os
import io
import sys
import time
import math
import requests
from binance.client import Client
from dotenv import load_dotenv
import top_gainers
import sell_all
import get_balance

# Load API keys from .env file
load_dotenv('.env')

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not API_KEY or not API_SECRET or not BOT_TOKEN or not CHAT_ID:
    print("Error: One or more environment variables are missing.")
    sys.exit(1)

# Initialize Binance client
client = Client(API_KEY, API_SECRET)

# Define DualOutput class for simultaneous console and buffer output
class DualOutput:
    def __init__(self):
        self.buffer = io.StringIO()
        self.console = sys.__stdout__

    def write(self, text):
        self.buffer.write(text)
        self.console.write(text)

    def flush(self):
        self.buffer.flush()
        self.console.flush()

    def getvalue(self):
        return self.buffer.getvalue()

def send_telegram_message(message):
    """Send a message via Telegram bot."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    try:
        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

def buy_token(symbol, usdt_amount):
    """Buy a token using a specified amount of USDT."""
    try:
        # Get the current price
        price_info = client.get_symbol_ticker(symbol=symbol)
        current_price = float(price_info['price'])

        # Calculate quantity to buy
        quantity = usdt_amount / current_price

        # Adjust quantity to lot size
        min_qty, step_size = get_lot_size(symbol)
        if min_qty is None or step_size is None:
            print(f"Cannot fetch lot size for {symbol}. Skipping...")
            return

        # Adjust quantity to comply with step size
        quantity = adjust_to_step_size(quantity, step_size)

        if quantity < min_qty:
            print(f"Quantity {quantity} is below the minimum allowed {min_qty} for {symbol}. Skipping...")
            return

        # Format quantity to correct precision
        step_size_str = "{:f}".format(step_size).rstrip('0')
        decimals = len(step_size_str.split('.')[-1]) if '.' in step_size_str else 0
        quantity_str = f"{{:.{decimals}f}}".format(quantity)

        # Remove any trailing zeros and unnecessary decimal points
        quantity_str = quantity_str.rstrip('0').rstrip('.')

        print(f"Placing order for {symbol} with quantity {quantity_str}...")

        # Place a market buy order
        order = client.create_order(
            symbol=symbol,
            side='BUY',
            type='MARKET',
            quantity=quantity_str
        )
        print(f"Buy order successful for {symbol}! Order details: {order}")
    except Exception as e:
        print(f"Error buying {symbol}: {e}")

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
    precision = int(round(-math.log(step_size, 10), 0))
    return round(quantity, precision)

def get_usdt_balance():
    """Helper function to get USDT balance."""
    account_info = client.get_account()
    balances = account_info['balances']
    for balance in balances:
        if balance['asset'] == 'USDT':
            return float(balance['free'])
    return 0.0

def get_total_usdt_value(balances):
    """Calculate the total USDT value from balances."""
    return sum(balance['usdt_value'] for balance in balances)

def generate_summary(initial_balances, initial_usdt_value, top_symbols, final_balances, final_usdt_value):
    """Generate a summary report of the script execution."""
    report_lines = [
        "🚀 *Bot Execution Summary* 🚀",
        "",
        "*Balances Before Execution:*",
        format_balances(initial_balances),
        f"\n*Initial Total Portfolio Value:* `{initial_usdt_value:.2f} USDT`",
        "",
        "*Top 5 Gainers Purchased:*",
        "\n".join([f"- `{symbol}`" for symbol in top_symbols]),
        "",
        "*Balances After Execution:*",
        format_balances(final_balances),
        f"\n*Final Total Portfolio Value:* `{final_usdt_value:.2f} USDT`",
        "",
        "Happy Trading! 📈"
    ]
    return '\n'.join(report_lines)

def format_balances(balances):
    """Format balances for display."""
    lines = []
    for balance in balances:
        asset = balance['asset']
        amount = balance['amount']
        usdt_value = balance['usdt_value']
        lines.append(f"- `{asset}`: {amount} (~{usdt_value:.2f} USDT)")
    return '\n'.join(lines)

def main():
    # Step 0: Get initial balances before selling
    print("Fetching balances before running the script...")
    initial_balances = get_balance.get_positive_balances(return_balances=True)
    initial_usdt_value = get_total_usdt_value(initial_balances)
    print(f"Initial Total Portfolio Value: {initial_usdt_value:.2f} USDT")

    # Step 1: Sell all tokens except USDT
    print("\nStep 1: Selling all tokens...")
    sell_all.main()
    time.sleep(10)  # Wait for sell orders to complete

    # Step 2: Display total USDT balance after selling
    usdt_balance = get_usdt_balance()
    print(f"\nTotal USDT balance after selling: {usdt_balance:.2f} USDT")

    # Step 3: Fetch top gainers
    print("\nStep 3: Fetching top gainers...")
    results = top_gainers.get_top_gainers()
    top_gainers.display_results(results)
    symbols = results['symbol'].tolist()

    # Limit to top 5 gainers
    top_symbols = symbols[:5]

    # If less than 5 top gainers, fill the rest with 'BTCUSDT'
    while len(top_symbols) < 5:
        top_symbols.append('BTCUSDT')

    print(f"Top 5 gainers (including BTC if less than 5): {top_symbols}")

    # Step 4: Buy top gainers
    print("\nStep 4: Buying top gainers...")
    num_tokens = len(top_symbols)
    for idx, symbol in enumerate(top_symbols):
        # Re-fetch USDT balance before each purchase
        usdt_balance = get_usdt_balance()
        tokens_left = num_tokens - idx
        if usdt_balance <= 0:
            print("No USDT available to buy tokens.")
            break

        # Distribute remaining USDT among the remaining tokens
        usdt_per_token = usdt_balance / tokens_left - 0.1  # Subtract estimated fees

        if usdt_per_token <= 0:
            print(f"Insufficient USDT to buy {symbol}. Skipping...")
            continue

        print(f"*******Buying {symbol} with {usdt_per_token:.2f} USDT...")
        buy_token(symbol, usdt_per_token)
        time.sleep(5)  # Delay to avoid rate limits

    # Step 5: Display updated balances
    print("\nStep 5: Displaying updated account balances...")
    final_balances = get_balance.get_positive_balances(return_balances=True)
    final_usdt_value = get_total_usdt_value(final_balances)
    print(f"Final Total Portfolio Value: {final_usdt_value:.2f} USDT")
    
    # Generate the summary
    summary = generate_summary(initial_balances, initial_usdt_value, top_symbols, final_balances, final_usdt_value)

    # Return data for the summary
    return initial_balances, initial_usdt_value, top_symbols, final_balances, final_usdt_value, summary

if __name__ == "__main__":
    
    while True:
        # Create an instance of DualOutput
        dual_output = DualOutput()
        # Redirect sys.stdout to dual_output
        sys.stdout = dual_output

        try:
            # Execute your main function and get summary data
            initial_balances, initial_usdt_value, top_symbols, final_balances, final_usdt_value, summary = main()
        except requests.exceptions.ConnectionError as ce:
            print(f"ConnectionError: {ce}. Retrying in 20 minutes.")
            sys.stdout = sys.__stdout__
            time.sleep(20 * 60)  # Wait for 20 minutes before retrying
            continue
        except requests.exceptions.Timeout as te:
            print(f"TimeoutError: {te}. Retrying in 1 minute.")
            sys.stdout = sys.__stdout__
            time.sleep(1 * 60)  # Wait for 1 minute before retrying
            continue
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 1 minute.")
            sys.stdout = sys.__stdout__
            time.sleep(1 * 60)  # Wait for 1 minute before retrying
            continue
        finally:
            # Restore standard stdout
            sys.stdout = sys.__stdout__

        # Get captured output
        captured_logs = dual_output.getvalue()

        # Filter lines that look like errors
        error_lines = []
        for line in captured_logs.splitlines():
            if any(keyword in line for keyword in ["Error", "Exception", "Failed","error", "exception", "failed"]):
                error_lines.append(line)
        
        # Send only errors (if any)
        if error_lines:
            error_text = "\n".join(error_lines)
            send_telegram_message(f"```\n{error_text}\n```")

        # Then send the summary
        send_telegram_message(summary)

        # Exit after successful execution
        break