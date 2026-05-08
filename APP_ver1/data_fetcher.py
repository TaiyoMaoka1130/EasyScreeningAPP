import yfinance as yf
import pandas as pd
import streamlit as st 




# --------------------------------------------------
# 株価データを取得する機能（関数）を定義します
# --------------------------------------------------
# ▼ 1時間のキャッシュを設定
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_data(ticker_symbol):
    print(f"【通信中】{ticker_symbol} の株価データを取得しています。少しお待ちください...")
    
    # yfinanceという道具を使って、指定した銘柄の情報を準備します
    stock_info = yf.Ticker(ticker_symbol)
    
    # 過去1ヶ月分（1mo）の日々のデータ（日足）を取得します
    # ※期間は "1d"(1日), "5d"(5日), "1mo"(1ヶ月), "1y"(1年) など変更可能です
    df = stock_info.history(period="6mo")
    
    return df

# --------------------------------------------------
# 実際にプログラムを動かす部分です
# --------------------------------------------------
if __name__ == "__main__":
    # 試しにトヨタ自動車のデータを取得してみます
    # ※日本の株をyfinanceで取得する場合、銘柄コードの後ろに「.T」をつけます
    target_ticker = "7203.T"
    
    # 上で作った機能を呼び出して、取得したデータを stock_df という箱に入れます
    stock_df = fetch_stock_data(target_ticker)
    
    # 取得したデータの中身を確認するために、画面に表示します
    print("\n【取得完了】直近5日間のデータは以下の通りです：")
    
    # .tail() は、表の一番下（最新の日付）から5行だけを表示する便利な機能です
    print(stock_df.tail())
    
    # --- 以下を data_fetcher.py の一番下に追記してください ---

@st.cache_data(ttl=86400) # 基本情報は1日1回の更新で十分なため長めにキャッシュ
# ▼ 24時間のキャッシュを設定
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamental_data(ticker_symbol):
    """
    PERや業種などのファンダメンタルズ情報を取得します。
    """
    try:
        # yfinanceからPERなどを抽出
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        data = {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "market_cap": info.get("marketCap")
        }
        return data
    except Exception:
        return {"per": None, "pbr": None, "market_cap": None}
    
    # --------------------------------------------------
# ファンダメンタルズ情報を取得する関数
# --------------------------------------------------
@st.cache_data(ttl=86400)
def fetch_fundamental_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # 値が存在しない場合は None を返す安全な取得方法
        data = {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "div_yield": info.get("dividendYield"),
            "market_cap": info.get("marketCap")
        }
        
        # ROEと配当利回りは小数（例: 0.05）で取得されるため、UIに合わせて％（例: 5.0）に変換します
        if data["roe"] is not None: data["roe"] *= 100
        if data["div_yield"] is not None: data["div_yield"] *= 100
            
        return data
    except Exception:
        return {"per": None, "pbr": None, "roe": None, "div_yield": None, "market_cap": None}