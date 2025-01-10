import os
import requests
import pandas as pd
from binance.client import Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv('.env')
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

client = Client(API_KEY, API_SECRET)

def get_top_200_symbols_with_data():
    """
    Fetch top 200 cryptocurrencies by market capitalization from CoinGecko API.
    Returns a list of dictionaries with symbol and rank.
    """
    try:
        # CoinGecko API endpoint for top cryptocurrencies
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 200,
            'page': 1,
            'sparkline': False
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        # Create a list of dictionaries with symbol and rank
        top_200_data = [
            {
                'symbol': f"{coin['symbol'].upper()}USDT", 
                'rank': coin['market_cap_rank']
            } 
            for coin in data
        ]
        return top_200_data
    
    except Exception as e:
        print(f"Error fetching top 200 cryptocurrencies: {e}")
        return []

def get_top_gainers():
    # Get top 200 symbols with their ranks
    top_200_data = get_top_200_symbols_with_data()
    
    # Create a dictionary for easy rank lookup
    top_200_ranks = {item['symbol']: item['rank'] for item in top_200_data}
    top_200_symbols = list(top_200_ranks.keys())
    
    # Get all ticker prices
    all_tickers = client.get_ticker()
    
    # Initialize list to store data
    crypto_data = []
    
    # Process each ticker
    for ticker in all_tickers:
        symbol = ticker['symbol']
        
        # Filter for USDT pairs in top 200
        if symbol.endswith('USDT') and symbol in top_200_symbols:
            try:
                # Fetch 7-day historical price data
                klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, "7 day ago UTC")
                if len(klines) < 7:
                    continue  # Not enough data
                
                # Get closing prices
                close_prices = [float(kline[4]) for kline in klines]
                current_price = close_prices[-1]
                seven_days_ago_price = close_prices[0]
                week_change = ((current_price - seven_days_ago_price) / seven_days_ago_price) * 100

                # 24h Price Change Percent
                price_change_percent_24h = float(ticker['priceChangePercent'])

                # 24h Volume
                volume_24h = float(ticker['quoteVolume'])

                crypto_data.append({
                    'symbol': symbol,
                    'market_cap_rank': top_200_ranks[symbol],
                    'current_price': current_price,
                    'week_price_change_percent': week_change,
                    '24h_price_change_percent': price_change_percent_24h,
                    '24h_volume': volume_24h
                })
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
    
    # Convert to DataFrame
    df = pd.DataFrame(crypto_data)
    
    # Filter for cryptos with positive 24h gains
    # And with more than 30% weekly gains
    df_filtered = df[
        (df['24h_price_change_percent'] > 0) & 
        (df['week_price_change_percent'] > 30)
    ]
    
    # Sort by 7-day price change
    df_sorted = df_filtered.sort_values('week_price_change_percent', ascending=False)
    
    return df_sorted

def display_results(df, top_n=5):
    print("\nTop", top_n, "Gainers in the Last 7 Days (Top 200, >30% Weekly Gain, Positive 24h Change):")
    print("=" * 100)
    print(f"{'Rank':<6}{'Symbol':<12}{'Current Price':<15}{'7d Change':<12}{'24h Change':<12}{'24H Volume':<20}")
    print("-" * 100)
    
    for idx, row in df.head(top_n).iterrows():
        print(
            f"{row['market_cap_rank']:<6}"
            f"{row['symbol']:<12} "
            f"${row['current_price']:<12.4f} "
            f"{row['week_price_change_percent']:>7.2f}% "
            f"{row['24h_price_change_percent']:>10.2f}% "
            f"{row['24h_volume']:>20,.2f}"
        )

if __name__ == "__main__":
    print("Fetching and analyzing crypto data from Binance...")
    results = get_top_gainers()
    display_results(results)

    symbols = results['symbol'].tolist()
    print(symbols)