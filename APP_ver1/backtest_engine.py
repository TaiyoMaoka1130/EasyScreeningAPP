import pandas as pd

def run_backtest_simulation(ticker, stock_name, df, buy_signals, sell_signals, stop_loss_pct, trailing_stop_pct=0.0):
    """
    時系列バックテストシミュレーションを実行する関数（銘柄名・トレイリングストップ対応版）
    """
    trades = []
    in_position = False
    entry_price = 0.0
    entry_date = None
    
    # 保有期間中の最高値を記録する変数
    highest_price_since_entry = 0.0 
    
    stop_ratio = 1.0 - (stop_loss_pct / 100.0) if stop_loss_pct > 0 else 0.0
    trailing_ratio = 1.0 - (trailing_stop_pct / 100.0) if trailing_stop_pct > 0 else 0.0

    for i in range(len(df) - 1):
        current_date = df.index[i]
        next_date = df.index[i + 1]
        
        if not in_position:
            if current_date in buy_signals:
                in_position = True
                entry_date = next_date
                entry_price = df.loc[next_date, 'Open']
                highest_price_since_entry = entry_price 
                
        else:
            current_low = df.loc[current_date, 'Low']
            current_high = df.loc[current_date, 'High']
            current_open = df.loc[current_date, 'Open']
            
            # 最高値の更新
            if current_high > highest_price_since_entry:
                highest_price_since_entry = current_high
            
            # 1. 損切りラインの抵触判定（絶対的な防衛線）
            if stop_ratio > 0:
                stop_price = entry_price * stop_ratio
                if current_open <= stop_price:
                    exit_price = current_open
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    trades.append({"ticker": ticker, "name": stock_name, "entry_date": entry_date.strftime('%Y-%m-%d'), "exit_date": current_date.strftime('%Y-%m-%d'), "entry_price": round(entry_price, 2), "exit_price": round(exit_price, 2), "return_pct": round(return_pct, 2), "exit_reason": "Stop Loss (Gap)"})
                    in_position = False; continue
                elif current_low <= stop_price:
                    exit_price = stop_price
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    trades.append({"ticker": ticker, "name": stock_name, "entry_date": entry_date.strftime('%Y-%m-%d'), "exit_date": current_date.strftime('%Y-%m-%d'), "entry_price": round(entry_price, 2), "exit_price": round(exit_price, 2), "return_pct": round(return_pct, 2), "exit_reason": "Stop Loss"})
                    in_position = False; continue

            # 2. トレイリングストップの抵触判定（高値からの下落）
            if trailing_ratio > 0:
                trailing_price = highest_price_since_entry * trailing_ratio
                
                # エントリー価格より上（含み益状態）でトレイリングラインが機能している場合のみ発動
                if trailing_price > entry_price:
                    if current_open <= trailing_price:
                        exit_price = current_open
                        return_pct = ((exit_price - entry_price) / entry_price) * 100
                        trades.append({"ticker": ticker, "name": stock_name, "entry_date": entry_date.strftime('%Y-%m-%d'), "exit_date": current_date.strftime('%Y-%m-%d'), "entry_price": round(entry_price, 2), "exit_price": round(exit_price, 2), "return_pct": round(return_pct, 2), "exit_reason": "Trailing Stop (Gap)"})
                        in_position = False; continue
                    elif current_low <= trailing_price:
                        exit_price = trailing_price
                        return_pct = ((exit_price - entry_price) / entry_price) * 100
                        trades.append({"ticker": ticker, "name": stock_name, "entry_date": entry_date.strftime('%Y-%m-%d'), "exit_date": current_date.strftime('%Y-%m-%d'), "entry_price": round(entry_price, 2), "exit_price": round(exit_price, 2), "return_pct": round(return_pct, 2), "exit_reason": "Trailing Stop"})
                        in_position = False; continue
            
            # 3. 通常の売りシグナル（SMA下抜け等）の発生判定
            if current_date in sell_signals:
                exit_price = df.loc[next_date, 'Open']
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append({"ticker": ticker, "name": stock_name, "entry_date": entry_date.strftime('%Y-%m-%d'), "exit_date": next_date.strftime('%Y-%m-%d'), "entry_price": round(entry_price, 2), "exit_price": round(exit_price, 2), "return_pct": round(return_pct, 2), "exit_reason": "Sell Signal"})
                in_position = False

    return trades