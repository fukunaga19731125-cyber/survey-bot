def calculate_survey_result(responses):
    """
    responses: リスト形式の回答データ [点数, 点数, ...]
    戻り値: 集計結果のメッセージ
    """
    if not responses:
        return "まだ回答がありません。"

    total = sum(responses)
    average = total / len(responses)
    
    # 簡単な診断ロジックの例
    if average >= 4:
        result_text = "素晴らしい結果です！"
    elif average >= 3:
        result_text = "まずまずの結果です。"
    else:
        result_text = "改善の余地がありそうです。"

    return f"回答数: {len(responses)}件\n合計点: {total}点\n平均点: {average:.1f}点\n\n診断結果: {result_text}"
