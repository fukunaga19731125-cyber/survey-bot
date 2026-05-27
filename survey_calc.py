def calculate_survey_result(message):
    """
    LINEから送られた文字を点数リストに変換して集計する。
    入力例:
    4,5,3
    4 5 3
    4
    5
    3
    """

    if not message:
        return "まだ回答がありません。"

    # 改行・カンマ・全角カンマをスペースに統一
    text = message.replace("\n", " ")
    text = text.replace(",", " ")
    text = text.replace("、", " ")

    parts = text.split()

    responses = []

    for part in parts:
        try:
            score = float(part)
            responses.append(score)
        except ValueError:
            return (
                "点数だけを入力してください。\n\n"
                "入力例:\n"
                "4,5,3\n\n"
                "または\n"
                "4 5 3\n\n"
                "または\n"
                "4\n5\n3"
            )

    if not responses:
        return "まだ回答がありません。"

    total = sum(responses)
    average = total / len(responses)

    # 簡単な診断ロジック
    if average >= 4:
        result_text = "素晴らしい結果です！"
    elif average >= 3:
        result_text = "まずまずの結果です。"
    else:
        result_text = "改善の余地がありそうです。"

    return (
        f"回答数: {len(responses)}件\n"
        f"合計点: {total:g}点\n"
        f"平均点: {average:.1f}点\n\n"
        f"診断結果: {result_text}"
    )
