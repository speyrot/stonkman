import sys
import yfinance as yf
import pandas as pd
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDateEdit, QTextEdit, QCheckBox
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon, QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        self.ticker_label = QLabel('Ticker Symbol:')
        self.ticker_input = QLineEdit()

        self.ma50_check = QCheckBox("Display 50-day MA")
        self.ma200_check = QCheckBox("Display 200-day MA")
        self.bb_check = QCheckBox("Display Bollinger Bands")
        self.macd_check = QCheckBox("Display MACD")
        self.ma50_check.setChecked(True)
        self.ma200_check.setChecked(True)
        self.bb_check.setChecked(True)
        self.macd_check.setChecked(True)

        
        self.start_label = QLabel('Start Date:')
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        
        self.end_label = QLabel('End Date:')
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        
        self.run_button = QPushButton('Run Analysis')
        self.run_button.clicked.connect(self.on_run)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(130)
        self.result_text.setFont(QFont('Arial', 15))
        
        self.figure = plt.figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        
        layout.addWidget(self.ma50_check)
        layout.addWidget(self.ma200_check)
        layout.addWidget(self.bb_check)
        layout.addWidget(self.macd_check)
        layout.addWidget(self.ticker_label)
        layout.addWidget(self.ticker_input)
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_date)
        layout.addWidget(self.end_label)
        layout.addWidget(self.end_date)
        layout.addWidget(self.run_button)
        layout.addWidget(self.result_text)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        self.setWindowTitle('Volume Profile Trading Strategy')
        self.setWindowIcon(QIcon('icon.png'))
    
    def on_run(self):
        ticker = self.ticker_input.text()
        start = self.start_date.date().toString('yyyy-MM-dd')
        end = self.end_date.date().toString('yyyy-MM-dd')
        self.analyze(ticker, start, end)

    def analyze(self, ticker, start, end):
        data = self.fetch_data(ticker, start, end)
        if data.empty:
            self.result_text.setText('No data found for the given range.')
            return
        poc, vah, val = self.calculate_volume_profile(data)
        additional_metrics = self.calculate_technical_indicators(data)
        self.show_results(poc, vah, val, additional_metrics, data)  # pass data for MACD analysis
        self.plot_data(data, poc, vah, val)

    def fetch_data(self, ticker, start, end):
        data = yf.download(ticker, start=start, end=end)
        return data

    def calculate_volume_profile(self, data):
        volume_max_idx = data['Volume'].idxmax()
        poc = data.loc[volume_max_idx, 'Close']
        top_volumes = data['Volume'].nlargest(10)
        vah = data.loc[top_volumes.index, 'High'].max()
        val = data.loc[top_volumes.index, 'Low'].min()
        return poc, vah, val

    def calculate_technical_indicators(self, data):
        # Moving Averages
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()
        
        # Bollinger Bands
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['STD20'] = data['Close'].rolling(window=20).std()
        data['Upper Band'] = data['MA20'] + (data['STD20'] * 2)
        data['Lower Band'] = data['MA20'] - (data['STD20'] * 2)

        # MACD
        data['EMA12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = data['EMA12'] - data['EMA26']
        data['Signal Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

        return data[['MA50', 'MA200', 'Upper Band', 'Lower Band', 'MACD', 'Signal Line']].iloc[-1].to_dict()

    def show_results(self, poc, vah, val, additional_metrics, data):
        result_text = (f"Point of Control (PoC): {poc}\n"
                    f"Value Area High (VAH): {vah}\n"
                    f"Value Area Low (VAL): {val}\n")

        if self.ma50_check.isChecked():
            result_text += f"50-day Moving Average: {additional_metrics['MA50']}\n"
        if self.ma200_check.isChecked():
            result_text += f"200-day Moving Average: {additional_metrics['MA200']}\n"
        
        # Append MACD analysis if checkbox is checked
        if self.macd_check.isChecked():
            macd = data['MACD'].iloc[-1]
            signal = data['Signal Line'].iloc[-1]
            macd_previous = data['MACD'].iloc[-2]
            signal_previous = data['Signal Line'].iloc[-2]

            # Determine the MACD trend and signal
            if macd > signal and macd_previous <= signal_previous:
                macd_analysis = "Bullish signal: MACD crossed above the signal line."
            elif macd < signal and macd_previous >= signal_previous:
                macd_analysis = "Bearish signal: MACD crossed below the signal line."
            else:
                macd_analysis = "No crossover: The MACD and signal line have not crossed."

            result_text += f"MACD: {macd:.2f}, Signal Line: {signal:.2f}\n{macd_analysis}\n"

        self.result_text.setText(result_text)

    def plot_data(self, data, poc, vah, val):
        self.figure.clear()

        if self.macd_check.isChecked():
            ax1 = self.figure.add_subplot(211)  # Price plot
            ax2 = self.figure.add_subplot(212)  # MACD plot
        else:
            ax1 = self.figure.add_subplot(111)  # Only price plot

        # Configure the subplot to make space for the legend
        self.figure.subplots_adjust(left=0.3, hspace=0.5 if self.macd_check.isChecked() else 0)

        # Plotting the closing price and indicators
        ax1.plot(data.index, data['Close'], label='Close Price', color='black')
        if self.ma50_check.isChecked():
            ax1.plot(data.index, data['MA50'], label='50-day MA', color='orange', linestyle='--')
        if self.ma200_check.isChecked():
            ax1.plot(data.index, data['MA200'], label='200-day MA', color='purple', linestyle='--')
        if self.bb_check.isChecked():
            ax1.plot(data.index, data['Upper Band'], label='Upper Bollinger Band', color='green')
            ax1.plot(data.index, data['Lower Band'], label='Lower Bollinger Band', color='red')
            ax1.fill_between(data.index, data['Upper Band'], data['Lower Band'], color='gray', alpha=0.3, label='Bollinger Band Range')

        ax1.axhline(poc, color='blue', linestyle='--', label='Point of Control (PoC)')
        ax1.axhline(vah, color='green', linestyle='--', label='Value Area High (VAH)')
        ax1.axhline(val, color='red', linestyle='--', label='Value Area Low (VAL)')
        ax1.set_title('Fat Stack Analysis')
        ax1.set_ylabel('Price')
        ax1.legend(loc='center left', bbox_to_anchor=(-0.5, 0.5))

        # Conditionally plot MACD if checkbox is checked
        if self.macd_check.isChecked():
            ax2.plot(data.index, data['MACD'], label='MACD', color='blue')
            ax2.plot(data.index, data['Signal Line'], label='Signal Line', color='red', linestyle='--')
            ax2.bar(data.index, data['MACD'] - data['Signal Line'], color='gray', alpha=0.3)  
            ax2.set_title('MACD')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('MACD')
            ax2.legend(loc='center left', bbox_to_anchor=(-0.5, 0.5))

        self.canvas.draw()

app = QApplication(sys.argv)
ex = TradingApp()
ex.show()
sys.exit(app.exec_())