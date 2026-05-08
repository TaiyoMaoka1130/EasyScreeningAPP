import pandas as pd

# --------------------------------------------------
# 条件とデータを照らし合わせる「判定エンジン」です
# --------------------------------------------------
def find_golden_cross(df):
    """
    df: SMA_5 と SMA_25 が追加されたデータ
    """
    # 1. 「1日前の状態」を調べます（.shift(1) は1行上のデータを取得する魔法の言葉です）
    # 1日前は、短期(SMA_5)が長期(SMA_25)よりも「下」にある、または「同じ」状態
    condition_yesterday = df['SMA_5'].shift(1) <= df['SMA_25'].shift(1)
    
    # 2. 「今日の状態」を調べます
    # 今日は、短期(SMA_5)が長期(SMA_25)よりも「上」にある状態
    condition_today = df['SMA_5'] > df['SMA_25']
    
    # 3. 2つの条件が「両方とも」当てはまる日を探します（ & は「かつ」という意味です）
    final_condition = condition_yesterday & condition_today
    
    # 4. 条件に合致した日付のデータだけを抜き出して返します
    result_df = df[final_condition]
    return result_df

# --------------------------------------------------
# 実際にプログラムを動かして確認する部分です
# --------------------------------------------------
if __name__ == "__main__":
    from data_fetcher import fetch_stock_data
    from indicators import add_sma
    
    target_ticker = "7203.T" # トヨタ自動車
    
    print("1. 半年分のデータを取得しています...")
    stock_df = fetch_stock_data(target_ticker)
    
    print("2. 材料（移動平均線）を追加しています...")
    stock_df = add_sma(stock_df, period=5)
    stock_df = add_sma(stock_df, period=25)
    
    print("3. スクリーニング条件（ゴールデンクロス）で判定しています...")
    # 上で作った判定エンジンに、材料を追加したデータを入れます
    result = find_golden_cross(stock_df)
    
    print("\n【判定結果】過去半年間で条件に合致した日は以下の通りです：")
    # 結果が空っぽ（合致する日がなかった）場合と、あった場合で表示を変えます
    if result.empty:
        print("合致する日はありませんでした。")
    else:
        # 見やすいように、必要な列だけを表示します
        print(result[['Close', 'SMA_5', 'SMA_25']])