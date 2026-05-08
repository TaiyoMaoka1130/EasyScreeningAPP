import pandas as pd
import numpy as np

# --------------------------------------------------
# 材料（テクニカル指標）の拡充モジュール
# ユーザーが自由に組み合わせられるよう、多様な指標を動的に計算します
# --------------------------------------------------

def add_sma(df, period):
    """単純移動平均線 (Simple Moving Average)"""
    col_name = f"SMA_{period}"
    df[col_name] = df['Close'].rolling(window=period).mean()
    return df

def add_ema(df, period):
    """指数平滑移動平均線 (Exponential Moving Average) : 直近の価格を重視する移動平均"""
    col_name = f"EMA_{period}"
    df[col_name] = df['Close'].ewm(span=period, adjust=False).mean()
    return df

def add_rsi(df, period=14):
    """RSI (Relative Strength Index) : 買われすぎ・売られすぎを示すオシレーター"""
    col_name = f"RSI_{period}"
    # 前日との価格差を計算します
    delta = df['Close'].diff()
    # 値上がり幅と値下がり幅を分離します
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 指定期間の平均を計算します
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # RSIの計算式を適用します
    rs = avg_gain / avg_loss
    df[col_name] = 100 - (100 / (1 + rs))
    return df

def add_macd(df, short_period=12, long_period=26, signal_period=9):
    """MACD (Moving Average Convergence Divergence) : トレンドの方向性と転換点を捉える指標"""
    # MACDライン = 短期EMA - 長期EMA
    short_ema = df['Close'].ewm(span=short_period, adjust=False).mean()
    long_ema = df['Close'].ewm(span=long_period, adjust=False).mean()
    df['MACD'] = short_ema - long_ema
    
    # シグナルライン = MACDラインのEMA
    df['MACD_Signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
    
    # ヒストグラム = MACDライン - シグナルライン
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df

def add_bollinger_bands(df, period=20, num_std=2):
    """ボリンジャーバンド : 価格の変動範囲（ボラティリティ）を示す指標"""
    sma = df['Close'].rolling(window=period).mean()
    # 標準偏差を計算します
    rolling_std = df['Close'].rolling(window=period).std()
    
    df[f'BB_Upper_{period}'] = sma + (rolling_std * num_std)
    df[f'BB_Lower_{period}'] = sma - (rolling_std * num_std)
    df[f'BB_Mid_{period}'] = sma
    return df