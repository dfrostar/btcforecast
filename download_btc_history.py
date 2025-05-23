import yfinance as yf
import pandas as pd

# Download historical BTC-USD data (max available)
df = yf.download('BTC-USD', start='2010-01-01')

# Reset index to get 'Date' as a column
df = df.reset_index()

# Save to CSV with required columns
# The app expects at least 'Date', 'Close', and 'Volume'
df[['Date', 'Close', 'Volume']].to_csv('btc_usd_full_history.csv', index=False)

print('Downloaded BTC-USD history and saved to btc_usd_full_history.csv')

if __name__ == "__main__":
    download_btc_history() 