import sys
import yfinance as yf
import pandas as pd
import numpy as np
import talib
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        self.ticker_label = QLabel('Stock Symbol:')
        self.ticker_input = QLineEdit()
        
        self.run_button = QPushButton('Run Strategy')
        self.run_button.clicked.connect(self.on_run)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        
        layout.addWidget(self.ticker_label)
        layout.addWidget(self.ticker_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.result_text)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        self.setWindowTitle('Stock Trading Strategy')
        self.setWindowIcon(QIcon('icon.png'))
    
    def on_run(self):
        ticker = self.ticker_input.text()
        self.execute_strategy(ticker)

    def execute_strategy(self, ticker):
        # Step 1: Fetch historical data
        data = self.fetch_data(ticker)
        if data.empty:
            self.result_text.setText('No data found for the given stock symbol.')
            return
        
        # Step 2: Calculate technical indicators
        data['MACD'], data['MACD_signal'], _ = talib.MACD(data['Close'])
        data['RSI'] = talib.RSI(data['Close'])
        data['upper_band'], data['middle_band'], data['lower_band'] = talib.BBANDS(data['Close'])
        data['OBV'] = talib.OBV(data['Close'], data['Volume'])
        data['ADX'] = talib.ADX(data['High'], data['Low'], data['Close'])

        # Step 3: Determine entry and exit points
        entry_points = self.find_entry_points(data)
        exit_points = self.find_exit_points(data)

        # Step 4: Execute trades
        trades = self.execute_trades(data, entry_points, exit_points)

        # Step 5: Display results
        self.display_results(trades)
        self.plot_data(data, entry_points, exit_points)

    def find_entry_points(self, data):
        entry_points = pd.DataFrame(index=data.index, columns=['MACD_cross', 'RSI', 'BB', 'OBV', 'ADX'])
        # MACD cross
        entry_points['MACD_cross'] = np.where((data['MACD'] > data['MACD_signal']) & (data['MACD'].shift(1) < data['MACD_signal'].shift(1)), True, False)
        # RSI
        entry_points['RSI'] = np.where(data['RSI'] < 30, True, False)
        # Bollinger Bands
        entry_points['BB'] = np.where((data['Close'] < data['lower_band']) & (data['Close'].shift(1) > data['lower_band'].shift(1)), True, False)
        # OBV
        entry_points['OBV'] = np.where((data['OBV'] > data['OBV'].rolling(20).mean()), True, False)
        # ADX
        entry_points['ADX'] = np.where(data['ADX'] > 25, True, False)
        return entry_points

    def find_exit_points(self, data):
        exit_points = pd.DataFrame(index=data.index, columns=['MACD_cross', 'RSI', 'BB', 'OBV', 'ADX'])
        # MACD cross
        exit_points['MACD_cross'] = np.where((data['MACD'] < data['MACD_signal']) & (data['MACD'].shift(1) > data['MACD_signal'].shift(1)), True, False)
        # RSI
        exit_points['RSI'] = np.where(data['RSI'] > 70, True, False)
        # Bollinger Bands
        exit_points['BB'] = np.where((data['Close'] > data['upper_band']) & (data['Close'].shift(1) < data['upper_band'].shift(1)), True, False)
        # OBV
        exit_points['OBV'] = np.where((data['OBV'] < data['OBV'].rolling(20).mean()), True, False)
        # ADX
        exit_points['ADX'] = np.where(data['ADX'] < 25, True, False)
        return exit_points

    def execute_trades(self, data, entry_points, exit_points):
        trades = pd.DataFrame(index=data.index, columns=['action'])
        in_trade = False
        for index, row in data.iterrows():
            if in_trade:
                if exit_points.loc[index].any():
                    trades.loc[index] = 'sell'
                    in_trade = False
                else:
                    trades.loc[index] = 'hold'
            else:
                if entry_points.loc[index].any():
                    if entry_points.loc[index, 'MACD_cross']:
                        trades.loc[index] = 'buy (MACD cross)'
                    elif entry_points.loc[index, 'RSI']:
                        trades.loc[index] = 'buy (RSI)'
                    elif entry_points.loc[index, 'BB']:
                        trades.loc[index] = 'buy (Bollinger Bands)'
                    elif entry_points.loc[index, 'OBV']:
                        trades.loc[index] = 'buy (OBV)'
                    elif entry_points.loc[index, 'ADX']:
                        trades.loc[index] = 'buy (ADX)'
                    else:
                        trades.loc[index] = 'wait'
                    in_trade = True
                else:
                    trades.loc[index] = 'hold'
        return trades

    def prompt_user_action(self):
        # Step 6: Prompt the user for action using QMessageBox
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Trading Action")
        msgBox.setText("Buy, Sell, or Wait?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            return 'buy'
        elif ret == QMessageBox.No:
            return 'sell'
        else:
            return 'wait'

    def display_results(self, trades):
        # Display trading results
        buy_signals = trades[trades['action'] == 'buy'].index
        sell_signals = trades[trades['action'] == 'sell'].index
        self.result_text.clear()
        self.result_text.append(f"Number of Buy Signals: {len(buy_signals)}")
        self.result_text.append(f"Number of Sell Signals: {len(sell_signals)}")
        self.result_text.append("\nBuy Signals:")
        self.result_text.append(', '.join([str(date) for date in buy_signals]))
        self.result_text.append("\nSell Signals:")
        self.result_text.append(', '.join([str(date) for date in sell_signals]))

    def fetch_data(self, ticker):
        # Fetch historical data using yfinance
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.Timedelta(days=14)
        data = yf.download(ticker, start=start_date, end=end_date, interval='5m')
        return data

    def plot_data(self, data, entry_points, exit_points):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(data.index, data['Close'], label='Close Price')
        # Plot entry and exit points
        ax.plot(entry_points[entry_points.any(axis=1)].index, data.loc[entry_points.any(axis=1), 'Close'], '^', markersize=10, color='g', lw=0, label='Buy Signal')
        ax.plot(exit_points[exit_points.any(axis=1)].index, data.loc[exit_points.any(axis=1), 'Close'], 'v', markersize=10, color='r', lw=0, label='Sell Signal')
        ax.legend()
        self.canvas.draw()

app = QApplication(sys.argv)
ex = TradingApp()
ex.show()
sys.exit(app.exec_())