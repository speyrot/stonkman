import sys
import logging
import yfinance as yf
import pandas as pd
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDateEdit, QTextEdit, QCheckBox, QHBoxLayout, QComboBox
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QIcon, QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        main_layout = QHBoxLayout()  
        main_layout.setSpacing(10)  

        # Left side for controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(3)
        controls_layout.setContentsMargins(5, 5, 5, 5)  

        # Right side for inputs
        input_layout = QVBoxLayout()
        input_layout.setSpacing(3)
        input_layout.setContentsMargins(5, 5, 5, 5)  

        # Adding widgets to controls_layout
        self.ma50_check = QCheckBox("Display 50-day MA")
        self.ma200_check = QCheckBox("Display 200-day MA")
        self.bb_check = QCheckBox("Display Bollinger Bands")
        self.macd_check = QCheckBox("Display MACD")
        self.rsi_check = QCheckBox("Display RSI")
        self.ma50_check.setChecked(False)
        self.ma200_check.setChecked(False)
        self.bb_check.setChecked(False)
        self.macd_check.setChecked(False)
        self.rsi_check.setChecked(False)

        for widget in [self.ma50_check, self.ma200_check, self.bb_check, self.macd_check, self.rsi_check]:
            controls_layout.addWidget(widget)
        controls_layout.addStretch(1)

        # Dropdown for selecting the date range
        self.range_label = QLabel('Select Date Range:')
        self.range_combo = QComboBox()
        self.range_combo.addItems(["1D", "5D", "1MO", "3MO", "6MO", "YTD", "1Y", "5Y", "MAX"])
        self.interval_label = QLabel('Select Interval:')
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1m", '2m', "5m", "30m", "1h", "1d", "1wk"])

        # Adding widgets to input_layout
        self.ticker_label = QLabel('Ticker Symbol:')
        self.ticker_input = QLineEdit()
        self.run_button = QPushButton('Run Analysis')
        self.run_button.clicked.connect(self.on_run)

        for widget in [self.ticker_label, self.ticker_input, self.range_label, self.range_combo, self.interval_label, self.interval_combo, self.run_button]:
            input_layout.addWidget(widget)
        input_layout.addStretch(1)

        # Add control and input layouts to main layout
        main_layout.addLayout(controls_layout, 1)
        main_layout.addLayout(input_layout, 1)

        # Result and Canvas area
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(130)
        self.result_text.setFont(QFont('Arial', 15))

        self.figure = plt.figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)

        vertical_layout_for_chart = QVBoxLayout()
        vertical_layout_for_chart.addWidget(self.result_text)
        vertical_layout_for_chart.addWidget(self.canvas)

        # Add this vertical layout to main layout with a higher stretch factor to give more space to the chart
        main_layout.addLayout(vertical_layout_for_chart, 3)

        self.setLayout(main_layout)
        self.setWindowTitle('Volume Profile Trading Strategy')
        self.setWindowIcon(QIcon('icon.png'))

    
    def on_run(self):
        ticker = self.ticker_input.text().strip().upper()
        range_selected = self.range_combo.currentText()  # Changed from currentData to currentText
        interval_selected = self.interval_combo.currentText()  # Changed from currentData to currentText
        logging.debug(f"Ticker: {ticker}, Range: {range_selected}, Interval: {interval_selected}")
        if ticker and range_selected and interval_selected:
            self.analyze(ticker, range_selected, interval_selected)
        else:
            self.result_text.setText("Please check your inputs. Missing or invalid values.")

    def analyze(self, ticker, range_selected, interval_selected):
        try:
            logging.debug(f"Attempting to download data for {ticker} with range {range_selected} and interval {interval_selected}")
            historical_data = yf.download(ticker, period=range_selected, interval=interval_selected)
            if historical_data.empty:
                self.result_text.setText('No data found for the given range and interval.')
                logging.error("No data returned from the API.")
                return
        except Exception as e:
            self.result_text.setText(f"Failed to fetch data: {str(e)}")
            logging.error(f"Failed to fetch data: {str(e)}")
            return
            
        # Define a conversion dictionary to adjust the rolling windows
        interval_to_minutes = {
            '1m': 1, '2m': 2, '5m': 5, '30m': 30, '1h': 60, '1d': 1440, '1wk': 10080
        }
        minutes_per_day = 1440  # Number of minutes in a day

        try:
            historical_data = yf.download(ticker, period=range_selected, interval=interval_selected)
            if historical_data.empty:
                self.result_text.setText('No data found for the given range and interval.')
                return
        except Exception as e:
            self.result_text.setText(f"Failed to fetch data: {str(e)}")
            return

        # Calculate rolling window size for daily metrics
        if interval_selected in interval_to_minutes:
            rolling_window = int(minutes_per_day / interval_to_minutes[interval_selected])  # Convert days to selected interval
        else:
            self.result_text.setText("Invalid interval selected.")
            return

        if self.rsi_check.isChecked() and historical_data is not None:
            historical_data = self.calculate_rsi(historical_data, interval_selected)

        if historical_data is not None:
            poc, vah, val = self.calculate_volume_profile(historical_data)
            if poc is None or vah is None or val is None:
                self.result_text.setText("Failed to calculate volume profile.")
                return

            additional_metrics = self.calculate_technical_indicators(historical_data, interval_selected)
            current_price = historical_data['Close'].iloc[-1]  # Get the most recent close price
            self.show_results(poc, vah, val, additional_metrics, historical_data, current_price)
            self.plot_data(historical_data, poc, vah, val)
        else:
            self.result_text.setText("Historical data is None after analysis.")

    def fetch_data(self, ticker, start, end):
        data = yf.download(ticker, start=start, end=end)
        return data

    def intervals_per_period(self, interval, period_days):
        """
        Converts a period in days to the number of intervals based on the interval duration in minutes.
        """
        interval_duration_minutes = {
            '1m': 1, '2m': 2, '5m': 5, '30m': 30, '1h': 60, '1d': 1440, '1wk': 10080
        }
        minutes_in_period = period_days * 1440  # Convert period_days to minutes
        return minutes_in_period // interval_duration_minutes[interval]

    # Ensure to call self.intervals_per_period() when needed in your methods
    def calculate_rsi(self, data, interval):
        if data is not None:
            period = self.intervals_per_period(interval, 14)  # Convert 14 days to intervals
            delta = data['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            data['RSI'] = rsi.fillna(50)
            return data
        else:
            return None

    def calculate_technical_indicators(self, data, interval):
        ma50_window = self.intervals_per_period(interval, 50)  # Convert 50 days to intervals
        ma200_window = self.intervals_per_period(interval, 200)  # Convert 200 days to intervals
        ma20_window = self.intervals_per_period(interval, 20)  # Convert 20 days to intervals

        # Moving Averages
        data['MA50'] = data['Close'].rolling(window=ma50_window).mean()
        data['MA200'] = data['Close'].rolling(window=ma200_window).mean()

        # Bollinger Bands
        data['MA20'] = data['Close'].rolling(window=ma20_window).mean()
        data['STD20'] = data['Close'].rolling(window=ma20_window).std()
        data['Upper Band'] = data['MA20'] + (data['STD20'] * 2)
        data['Lower Band'] = data['MA20'] - (data['STD20'] * 2)

        # MACD
        ema12_days = 12
        ema26_days = 26
        ema12_window = self.intervals_per_period(interval, ema12_days)
        ema26_window = self.intervals_per_period(interval, ema26_days)
        data['EMA12'] = data['Close'].ewm(span=ema12_window, adjust=False).mean()
        data['EMA26'] = data['Close'].ewm(span=ema26_window, adjust=False).mean()
        data['MACD'] = data['EMA12'] - data['EMA26']
        data['Signal Line'] = data['MACD'].ewm(span=self.intervals_per_period(interval, 9), adjust=False).mean()

        return data[['MA50', 'MA200', 'Upper Band', 'Lower Band', 'MACD', 'Signal Line']].iloc[-1].to_dict()

    def calculate_volume_profile(self, data):
        if data.empty:
            return None, None, None  # Safeguard against empty data frames

        if 'Volume' in data.columns and not data['Volume'].dropna().empty:
            volume_max_idx = data['Volume'].idxmax()
            poc = data.loc[volume_max_idx, 'Close'] if volume_max_idx in data.index else None
            top_volumes = data['Volume'].nlargest(10)

            if not top_volumes.empty:
                vah_indices = top_volumes.index.intersection(data.index)
                vah = data.loc[vah_indices, 'High'].max() if not vah_indices.empty else None
                val_indices = top_volumes.index.intersection(data.index)
                val = data.loc[val_indices, 'Low'].min() if not val_indices.empty else None
            else:
                vah = val = None
        else:
            poc = vah = val = None
        return poc, vah, val

    def show_results(self, poc, vah, val, additional_metrics, data, current_price):
        result_text = (f"Most Recent Close Price: {current_price}\n"  
                    f"Point of Control (PoC): {poc}\n"
                    f"Value Area High (VAH): {vah}\n"
                    f"Value Area Low (VAL): {val}\n")

        if self.ma50_check.isChecked():
            result_text += f"50-day Moving Average: {additional_metrics['MA50']}\n"
        if self.ma200_check.isChecked():
            result_text += f"200-day Moving Average: {additional_metrics['MA200']}\n"

        if self.macd_check.isChecked():
            macd = data['MACD'].iloc[-1]
            signal = data['Signal Line'].iloc[-1]

            # Check if DataFrame has at least two rows
            if len(data) >= 2:
                macd_previous = data['MACD'].iloc[-2]
                signal_previous = data['Signal Line'].iloc[-2]

                # Determine the MACD trend and signal
                if macd > signal and macd_previous <= signal_previous:
                    macd_analysis = "Bullish signal: MACD crossed above the signal line."
                elif macd < signal and macd_previous >= signal_previous:
                    macd_analysis = "Bearish signal: MACD crossed below the signal line."
                else:
                    macd_analysis = "No crossover: The MACD and signal line have not crossed."
            else:
                macd_analysis = "Insufficient data to analyze MACD crossover."

            result_text += f"MACD: {macd:.2f}, Signal Line: {signal:.2f}\n{macd_analysis}\n"

        self.result_text.setText(result_text)

    def plot_data(self, data, poc, vah, val):
        self.figure.clear()
        # Calculate the number of plots based on user selections
        num_plots = 1 + (self.macd_check.isChecked()) + (self.rsi_check.isChecked())

        # Adjust figure layout to optimize space
        self.figure.subplots_adjust(left=0.1, right=0.75, hspace=0.5, bottom=0.1)

        # Price plot will always be present
        ax1 = self.figure.add_subplot(num_plots, 1, 1)
        ax1.plot(data.index, data['Close'], label='Close Price', color='black')
        if self.ma50_check.isChecked():
            ax1.plot(data.index, data['MA50'], label='50-day MA', color='orange', linestyle='--')
        if self.ma200_check.isChecked():
            ax1.plot(data.index, data['MA200'], label='200-day MA', color='purple', linestyle='--')
        if self.bb_check.isChecked():
            ax1.plot(data.index, data['Upper Band'], label='Upper Bollinger Band', color='green')
            ax1.plot(data.index, data['Lower Band'], label='Lower Bollinger Band', color='red')
            ax1.fill_between(data.index, data['Upper Band'], data['Lower Band'], color='gray', alpha=0.3)

        ax1.axhline(poc, color='blue', linestyle='--')
        ax1.axhline(vah, color='green', linestyle='--')
        ax1.axhline(val, color='red', linestyle='--')
        ax1.set_title('Price and FRVP')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left', bbox_to_anchor=(1,1))

        current_plot_index = 2 
        if self.macd_check.isChecked():
            ax_macd = self.figure.add_subplot(num_plots, 1, current_plot_index)
            ax_macd.plot(data.index, data['MACD'], label='MACD', color='blue')
            ax_macd.plot(data.index, data['Signal Line'], label='Signal Line', color='red', linestyle='--')
            ax_macd.bar(data.index, data['MACD'] - data['Signal Line'], color='gray', alpha=0.3)
            ax_macd.set_title('MACD Indicator')
            ax_macd.set_ylabel('MACD Value')
            ax_macd.legend(loc='upper left', bbox_to_anchor=(1,1))
            current_plot_index += 1

        if self.rsi_check.isChecked():
            ax_rsi = self.figure.add_subplot(num_plots, 1, current_plot_index)
            ax_rsi.plot(data.index, data['RSI'], label='RSI', color='purple')
            ax_rsi.axhline(70, color='red', linestyle='--', label='Overbought (70)')
            ax_rsi.axhline(30, color='green', linestyle='--', label='Oversold (30)')
            ax_rsi.set_title('RSI Indicator')
            ax_rsi.set_ylabel('RSI Value')
            ax_rsi.set_ylim([0, 100])
            ax_rsi.legend(loc='upper left', bbox_to_anchor=(1,1))

        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TradingApp()
    ex.show()
    sys.exit(app.exec_())