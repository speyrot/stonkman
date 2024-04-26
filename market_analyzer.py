import sys
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QLineEdit, QTextEdit, QLabel, QHBoxLayout)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, FuncFormatter

def fetch_data(symbol, interval='1d', period='1y'):
    data = yf.download(symbol, interval=interval, period=period)
    if not data.empty:
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        return data
    else:
        print("No data found for the given symbol.")
        return None

def calculate_volume_profile(data):
    if 'volume' in data.columns:
        data.loc[:, 'volume'] = pd.to_numeric(data['volume'])
        volume_profile = data.groupby('close')['volume'].sum()
        return volume_profile
    else:
        print("Volume column not found in the data.")
        return None

def calculate_market_profile(data):
    if 'close' in data.columns:
        data.loc[:, 'close'] = pd.to_numeric(data['close'])
        sorted_data = data.sort_values(by='close')
        market_profile = sorted_data['close'].value_counts().sort_index()
        return market_profile

def analyze_entry_points(volume_profile, market_profile):
    high_volume_levels = volume_profile[volume_profile > volume_profile.mean() + volume_profile.std()]
    significant_prices = market_profile[market_profile > market_profile.mean() + market_profile.std()]
    potential_entries = high_volume_levels.index.intersection(significant_prices.index)
    return potential_entries

def interpret_results(volume_profile, market_profile, entry_points, data):
    interpretations = []
    currency = "$"
    current_price = data['close'].iloc[-1]
    sma_short = data['close'].rolling(window=10).mean().iloc[-1]
    sma_long = data['close'].rolling(window=30).mean().iloc[-1]
    trend = "upward" if sma_short > sma_long else "downward"
    atr = data['close'].rolling(window=14).apply(lambda x: max(x) - min(x)).iloc[-1]  # ATR for volatility

    target_buy_price = current_price - atr  # Buy target is one ATR below current price
    target_sell_price = current_price + atr  # Sell target is one ATR above current price

    if trend == "upward":
        interpretations.append(f"You should consider buying the stock at {currency}{target_buy_price:.2f} and aim to sell near {currency}{target_sell_price:.2f}, aligning with the upward trend.")
    else:
        interpretations.append(f"You should consider selling the stock at {currency}{target_sell_price:.2f} and aim to rebuy near {currency}{target_buy_price:.2f}, aligning with the downward trend.")

    return "\n".join(interpretations)

def create_gui():
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    label = QLabel("Enter Stock Symbol:")
    layout.addWidget(label)
    symbol_entry = QLineEdit()
    layout.addWidget(symbol_entry)
    fetch_button = QPushButton('Fetch Data and Analyze')
    layout.addWidget(fetch_button)
    result_text = QTextEdit()
    result_text.setReadOnly(True)
    layout.addWidget(result_text)
    plot_volume_button = QPushButton('Plot Volume Profile')
    plot_market_button = QPushButton('Plot Market Profile')
    button_layout = QHBoxLayout()
    button_layout.addWidget(plot_volume_button)
    button_layout.addWidget(plot_market_button)
    layout.addLayout(button_layout)
    canvas = FigureCanvas(Figure(figsize=(5, 3)))
    layout.addWidget(canvas)

    def on_plot_volume():
        if 'volume_profile' in globals():
            canvas.figure.clear()
            ax = canvas.figure.add_subplot(111)
            volume_profile.plot(kind='bar', ax=ax)
            ax.set_title('Volume Profile')
            ax.set_xlabel('Price')
            ax.set_ylabel('Volume')
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.3f}'))
            ax.tick_params(axis='x', rotation=45)
            canvas.figure.subplots_adjust(bottom=0.5)
            canvas.draw()

    def on_plot_market():
        if 'market_profile' in globals():
            canvas.figure.clear()
            ax = canvas.figure.add_subplot(111)
            market_profile.plot(kind='bar', ax=ax)
            ax.set_title('Market Profile')
            ax.set_xlabel('Price')
            ax.set_ylabel('Frequency')
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.3f}'))
            ax.tick_params(axis='x', rotation=45)
            canvas.figure.subplots_adjust(bottom=0.5)
            canvas.draw()

    def on_fetch_data():
        symbol = symbol_entry.text()
        global data, volume_profile, market_profile
        data = fetch_data(symbol)
        if data is not None:
            volume_profile = calculate_volume_profile(data)
            market_profile = calculate_market_profile(data)
            entry_points = analyze_entry_points(volume_profile, market_profile)
            interpretation = interpret_results(volume_profile, market_profile, entry_points, data)
            result_text.setText(interpretation)
        else:
            result_text.setText("Failed to fetch data. Check the symbol and try again.")

    fetch_button.clicked.connect(on_fetch_data)
    plot_volume_button.clicked.connect(on_plot_volume)
    plot_market_button.clicked.connect(on_plot_market)

    window.setWindowTitle("Stock Analyzer")
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    create_gui()