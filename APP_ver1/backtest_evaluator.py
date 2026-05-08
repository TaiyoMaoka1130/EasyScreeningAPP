import pandas as pd

def calculate_metrics(trade_history):
    """
    トレード履歴のリストから、バックテストのコア評価指標を計算する関数
    
    :param trade_history: 以下のような辞書のリストを想定
        [
            {"ticker": "7203", "entry_date": "2026-01-05", "exit_date": "2026-01-20", "return_pct": 10.5, "result": "win"},
            {"ticker": "7203", "entry_date": "2026-02-10", "exit_date": "2026-02-15", "return_pct": -4.2, "result": "loss"},
            ...
        ]
    :return: 評価指標が格納された辞書
    """
    if not trade_history or len(trade_history) == 0:
        return None

    df_trades = pd.DataFrame(trade_history)
    total_trades = len(df_trades)

    # 勝ちトレードと負けトレードの分類（0%は手数料負けを考慮して負けに含めるのが一般的）
    wins = df_trades[df_trades['return_pct'] > 0]
    losses = df_trades[df_trades['return_pct'] <= 0]

    # 勝率の計算 (%)
    win_rate = (len(wins) / total_trades) * 100

    # 平均利益と平均損失の計算 (%)
    avg_profit = wins['return_pct'].mean() if not wins.empty else 0.0
    avg_loss = losses['return_pct'].mean() if not losses.empty else 0.0

    # リスクリワード・レシオの計算 (絶対値で計算)
    if avg_loss != 0:
        risk_reward = abs(avg_profit / avg_loss)
    else:
        # 損失が一度もない場合の例外処理
        risk_reward = float('inf') 

    # 期待値 (EV) の計算 (%)
    expected_value = (win_rate / 100 * avg_profit) + ((100 - win_rate) / 100 * avg_loss)

    return {
        "総トレード数": total_trades,
        "勝率": round(win_rate, 2),
        "平均利益": round(avg_profit, 2),
        "平均損失": round(avg_loss, 2),
        "リスクリワード": round(risk_reward, 2),
        "期待値": round(expected_value, 2)
    }