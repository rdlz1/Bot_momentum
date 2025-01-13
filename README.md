# Bot Momentum

This Python script automates:
- Selling all tokens except USDT
- Identifying the top weekly gainers
- Buying the top gainers using available USDT
- Sending errors to a Telegram chat

Installation & Setup
Clone the Repository:
git clone https://github.com/rdlz1/Bot_momentum.git

Create/Activate a Virtual Environment (optional):
python3 -m venv .venv
source .venv/bin/activate

Install Dependencies:
pip install -r requirements.txt

Configure Environment Variables (.env):
BINANCE_API_KEY=…
BINANCE_API_SECRET=…
TELEGRAM_BOT_TOKEN=…
TELEGRAM_CHAT_ID=…

Run the Script:
run_bot.sh
