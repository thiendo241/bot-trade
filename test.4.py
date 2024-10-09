import pandas as pd
import pandas_ta as ta
import ccxt
import asyncio 
import sys

# Đặt lại bộ mã hóa mặc định
sys.stdout.reconfigure(encoding='utf-8')
# Kết nối với sàn giao dịch OKX
exchange = ccxt.okx({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
})

# Giả sử bạn đã có dữ liệu OHLC trong DataFrame df
df = pd.read_csv('dữ liệu csv đã được sữ lí/output/combined_data.csv')
#input_dir = r'C:\Users\ADMIN\OneDrive\trở thành thiên tài\tổng hợp dữ liệu csv của 5 đồng coin'
# 1. Tính RSI cơ bản và nâng cao
def calculate_rsi(df):
    df['RSI'] = ta.rsi(df['Close'], length=14)
    return df

def rsi_divergence(df, rsi_period=14):
    df['RSI'] = ta.rsi(df['Close'], length=rsi_period)
    df['RSI_Divergence'] = 0
    for i in range(1, len(df) - 1):
        if df['Close'][i] > df['Close'][i - 1] and df['RSI'][i] < df['RSI'][i - 1]:
            df.at[i, 'RSI_Divergence'] = 1  # Phân kỳ thường
        elif df['Close'][i] < df['Close'][i - 1] and df['RSI'][i] > df['RSI'][i - 1]:
            df.at[i, 'RSI_Divergence'] = -1  # Phân kỳ kín
    return df

# 2. Tính Accumulation/Distribution Line (A/D Line)
def calculate_ad(df):
    df['AD'] = ta.ad(df['High'], df['Low'], df['Close'], df['Volume'])
    return df

# 3. Xác định các vùng Order Block (OB) và Imbalance
def find_order_blocks(df):
    order_blocks = []
    for i in range(1, len(df) - 1):
        if df['Close'][i] > df['Open'] and df['Close'][i] > df['Close'][i - 1] and df['Close'][i] > df['Close'][i + 1]:
            order_blocks.append((df.index[i], 'Bullish OB'))
        elif df['Close'][i] < df['Open'] and df['Close'][i] < df['Close'][i - 1] and df['Close'][i] < df['Close'][i + 1]:
            order_blocks.append((df.index[i], 'Bearish OB'))
    return order_blocks

# 4. Xác định các mức Fibonacci
def calculate_fibonacci_levels(df, start, end):
    diff = df['High'][end] - df['Low'][start]
    levels = {
        '0.236': df['High'][end] - diff * 0.236,
        '0.382': df['High'][end] - diff * 0.382,
        '0.5': df['High'][end] - diff * 0.5,
        '0.618': df['High'][end] - diff * 0.618,
        '0.786': df['High'][end] - diff * 0.786,
    }
    return levels

# 5. Xác định Key Levels
def find_key_levels(df):
    key_levels = []
    for i in range(1, len(df) - 1):
        if df['Close'][i] < df['Close'][i - 1] and df['Close'][i] < df['Close'][i + 1]:
            key_levels.append((df.index[i], 'Support'))
        elif df['Close'][i] > df['Close'][i - 1] and df['Close'][i] > df['Close'][i + 1]:
            key_levels.append((df.index[i], 'Resistance'))
    return key_levels

# 6. Tính chỉ báo UT Bot
def ut_bot(df):
    df['UT_Buy'] = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1))
    df['UT_Sell'] = (df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1))
    return df

# 7. Chia dữ liệu theo khung thời gian
def resample_data(df, timeframe):
    df_resampled = df.resample(timeframe).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    return df_resampled

# 8. Tính các chỉ báo khác
def calculate_indicators(df):
    df['EMA_34'] = ta.ema(df['Close'], length=34)
    df['EMA_89'] = ta.ema(df['Close'], length=89)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['SuperTrend'] = ta.supertrend(df['High'], df['Low'], df['Close'], length=7, multiplier=3)['SUPERTd_7_3.0']
    df['STC'] = ta.stc(df['Close'], window_slow=50, window_fast=23, cycle=10)
    df['Donchian_High'] = df['High'].rolling(window=20).max()
    df['Donchian_Low'] = df['Low'].rolling(window=20).min()
    return df

# 9. Kiểm tra điều kiện vào lệnh
def check_entry_conditions(df, order_blocks, fibonacci_levels, key_levels):
    entries = []
    for ob in order_blocks:
        ob_index, ob_type = ob
        # Điều kiện a: Order Block
        condition_a = ob_type == 'Bullish OB' and fibonacci_levels['0.618'] <= df['Close'][ob_index] <= fibonacci_levels['0.786']
        # Điều kiện b: RSI phân kỳ
        condition_b = df['RSI_Divergence'][ob_index] == 1
        # Điều kiện c: A/D Line tăng
        condition_c = df['AD'][ob_index] > df['AD'][ob_index - 1]
        # Điều kiện d: Key Level
        condition_d = any(k[0] == ob_index and k[1] == 'Support' for k in key_levels)
        # Điều kiện e: UT Bot
        condition_e = df['UT_Buy'][ob_index] if ob_type == 'Bullish OB' else df['UT_Sell'][ob_index]
        # Điều kiện f: SuperTrend, Donchian, STC
        condition_f = (df['SuperTrend'][ob_index] == 1 and df['Close'][ob_index] > df['Donchian_High'][ob_index] and df['STC'][ob_index] > 50) if ob_type == 'Bullish OB' else (df['SuperTrend'][ob_index] == -1 and df['Close'][ob_index] < df['Donchian_Low'][ob_index] and df['STC'][ob_index] < 50)
        
        # Kiểm tra các điều kiện
        if condition_a and condition_b and condition_c and condition_d and condition_e and condition_f:
            entries.append((df.index[ob_index], 'Buy' if ob_type == 'Bullish OB' else 'Sell'))
    return entries

# 10. Đặt lệnh và tp sl + vs logic quản lí vốn 

# Hàm đặt lệnh với các quy tắc chốt lời/cắt lỗ
def place_orders(entries, balance, symbol, leverage=20):
    for entry in entries:
        entry_index, entry_type = entry
        amount = balance * 0.05  # 5% tài khoản
        price = df['Close'][entry_index]
        
        if entry_type == 'Buy':
            order = exchange.create_order(
                symbol=symbol,
                type='limit',
                side='buy',
                amount=amount,
                price=price,
                params={'leverage': leverage}  # Đòn bẩy x20
            )
            # Thêm các mức chốt lời và cắt lỗ
            tp_levels = [1.5, 2, 3, 4]
            sl_price = price * 0.95  # Giả sử cắt lỗ 5%
            for tp in tp_levels:
                tp_price = price * (1 + tp / 100)
                exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side='sell',
                    amount=amount * 0.1 if tp > 1.5 else amount * 0.5,
                    price=tp_price,
                    params={'leverage': leverage}  # Đòn bẩy x20
                )
            exchange.create_order(
                symbol=symbol,
                type='stop_loss_limit',
                side='sell',
                amount=amount,
                price=sl_price,
                params={'leverage': leverage}  # Đòn bẩy x20
            )
        elif entry_type == 'Sell':
            order = exchange.create_order(
                symbol=symbol,
                type='limit',
                side='sell',
                amount=amount,
                price=price,
                params={'leverage': leverage}  # Đòn bẩy x20
            )
            # Thêm các mức chốt lời và cắt lỗ
            tp_levels = [1.5, 2, 3, 4]
            sl_price = price * 1.05  # Giả sử cắt lỗ 5%
            for tp in tp_levels:
                tp_price = price * (1 - tp / 100)
                exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side='buy',
                    amount=amount * 0.1 if tp > 1.5 else amount * 0.5,
                    price=tp_price,
                    params={'leverage': leverage}  # Đòn bẩy x20
                )
            exchange.create_order(
                symbol=symbol,
                type='stop_loss_limit',
                side='buy',
                amount=amount,
                price=sl_price,
                params={'leverage': leverage}  # Đòn bẩy x20
            )
        print(order)
# Hàm lấy ngày tháng hiện tại từ dữ liệu
def get_current_date(index, df):
    return df.index[index]
# Hàm kiểm tra số lệnh thua và dừng giao dịch nếu cần

def check_loss_limits(trade_results, current_date, max_daily_losses=5, max_weekly_losses=15, max_monthly_losses=30):
    current_day = current_date.date()
    current_week = current_date.isocalendar()[1]
    current_month = current_date.month
    
    daily_losses = sum(1 for result in trade_results if result['date'].date() == current_day and result['outcome'] == 'loss')
    weekly_losses = sum(1 for result in trade_results if result['date'].isocalendar()[1] == current_week and result['outcome'] == 'loss')
    monthly_losses = sum(1 for result in trade_results if result['date'].month == current_month and result['outcome'] == 'loss')
    
    if daily_losses >= max_daily_losses or weekly_losses >= max_weekly_losses or monthly_losses >= max_monthly_losses:
        return False  # Dừng giao dịch
    return True  # Tiếp tục giao dịch

async def main():
    coins = ['BTC', 'ETH', 'LTC' 'BCH' 'SOL' 'DOGE']  # Danh sách các coin cần quét
    timeframes = ['15T', '1h', '4h', '1d']  # Danh sách các khung thời gian cần quét
    dataframes = await scan_multiple_coins_and_timeframes(coins, timeframes)
    
    trade_results = []  # Danh sách kết quả giao dịch
    for symbol, df in zip(coins, dataframes):
        df = calculate_indicators(df)
        df = calculate_rsi(df)
        df = rsi_divergence(df)
        
        order_blocks = find_order_blocks(df)
        fibonacci_levels = calculate_fibonacci_levels(df, 0, len(df) - 1)
        key_levels = find_key_levels(df)
        
        entries = check_entry_conditions(df, order_blocks, fibonacci_levels, key_levels)
        
        if check_loss_limits(trade_results):
            place_orders(entries, balance=100, symbol=symbol)  # Giả sử số dư tài khoản là 100 USD
        else:
            print("Dừng giao dịch do vượt quá giới hạn thua lỗ")
# 11. Quét nhiều coin
def scan_multiple_coins(coins, timeframe):
    all_entries = []
    for coin in coins:
        df = exchange.fetch_ohlcv(coin, timeframe)
        df = pd.DataFrame(df, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        df = calculate_indicators(df)
        df = calculate_rsi(df)
        df = rsi_divergence(df)
        
        order_blocks = find_order_blocks(df)
        fibonacci_levels = calculate_fibonacci_levels(df, 0, len(df) - 1)
        key_levels = find_key_levels(df)
        
        entries = check_entry_conditions(df, order_blocks, fibonacci_levels, key_levels)
        all_entries.extend(entries)
    
    return all_entries

# 12. In ra các thông tin cần thiết
def print_backtest_results(results):
    print("Start:", results['Start'])
  

# Hàm không đồng bộ để lấy dữ liệu OHLCV
async def fetch_ohlcv(symbol, timeframe):
    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Hàm không đồng bộ để quét nhiều coin và nhiều khung thời gian
async def scan_multiple_coins_and_timeframes(coins, timeframes):
    tasks = []
    for coin in coins:
        for timeframe in timeframes:
            tasks.append(fetch_ohlcv(coin, timeframe))
    dataframes = await asyncio.gather(*tasks)
    return dataframes



# Chạy hàm chính
asyncio.run(main())

import datetime

# Biến toàn cục để lưu trữ thời gian dừng giao dịch
stop_trading_until = None

def check_loss_limits(trade_results, current_date, max_daily_losses=5, max_weekly_losses=15, max_monthly_losses=30):
    global stop_trading_until
    
    if stop_trading_until and current_date < stop_trading_until:
        return False  # Vẫn trong thời gian dừng giao dịch
    
    current_day = current_date.date()
    current_week = current_date.isocalendar()[1]
    current_month = current_date.month
    
    daily_losses = sum(1 for result in trade_results if result['date'].date() == current_day and result['outcome'] == 'loss')
    weekly_losses = sum(1 for result in trade_results if result['date'].isocalendar()[1] == current_week and result['outcome'] == 'loss')
    monthly_losses = sum(1 for result in trade_results if result['date'].month == current_month and result['outcome'] == 'loss')
    
    if daily_losses >= max_daily_losses:
        stop_trading_until = datetime.datetime.combine(current_day + datetime.timedelta(days=1), datetime.time.min)
        return False  # Dừng giao dịch đến hết ngày
    elif weekly_losses >= max_weekly_losses:
        next_week_start = current_date + datetime.timedelta(days=(7 - current_date.weekday()))
        stop_trading_until = datetime.datetime.combine(next_week_start, datetime.time.min)
        return False  # Dừng giao dịch đến hết tuần
    elif monthly_losses >= max_monthly_losses:
        next_month_start = (current_date.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        stop_trading_until = datetime.datetime.combine(next_month_start, datetime.time.min)
        return False  # Dừng giao dịch đến hết tháng
    return True  # Tiếp tục giao dịch

