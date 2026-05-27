import re


def parse_station(station_text, pitch=20.0):
    """
    測点文字を距離に変換する。
    例:
    No.1       -> 20.0
    No.1+2.0   -> 22.0
    """
    text = station_text.strip()
    text = text.replace("Ｎｏ", "No")
    text = text.replace("ｎｏ", "No")
    text = text.replace("NO", "No")
    text = text.replace("no", "No")
    text = text.replace("＋", "+")
    text = text.replace("．", ".")

    pattern = r"No\.?\s*(\d+)(?:\+([0-9.]+))?"
    match = re.search(pattern, text)

    if not match:
        raise ValueError(f"測点の形式が読み取れません: {station_text}")

    no_number = int(match.group(1))
    plus_value = float(match.group(2)) if match.group(2) else 0.0

    return no_number * pitch + plus_value


def calculate_road_center_height(message):
    """
    道路計画中心高を計算する。
    入力例:
    計画高
    ピッチ=20
    No.1,10.000
    No.2,9.800
    求める=No.1+2.0
    """

    lines = [line.strip() for line in message.splitlines() if line.strip()]

    pitch = 20.0
    target_station_text = None
    points = []

    for line in lines:
        line = line.replace("，", ",")
        line = line.replace("＝", "=")

        if line.startswith("ピッチ"):
            try:
                pitch = float(line.split("=")[1].strip())
            except Exception:
                return "ピッチの指定が読み取れません。例: ピッチ=20"

        elif line.startswith("求める"):
            try:
                target_station_text = line.split("=")[1].strip()
            except Exception:
                return "求める測点が読み取れません。例: 求める=No.1+2.0"

        elif line.lower().startswith("no") or line.startswith("No") or line.startswith("Ｎｏ"):
            parts = [p.strip() for p in line.split(",")]

            if len(parts) != 2:
                return "測点と高さはカンマで区切ってください。例: No.1,10.000"

            station_text = parts[0]
            height_text = parts[1]

            try:
                distance = parse_station(station_text, pitch)
                height = float(height_text)
                points.append({
                    "station": station_text,
                    "distance": distance,
                    "height": height
                })
            except Exception as e:
                return f"測点データが読み取れません。\n{str(e)}"

    if not points:
        return (
            "計画高データがありません。\n\n"
            "入力例:\n"
            "計画高\n"
            "ピッチ=20\n"
            "No.1,10.000\n"
            "No.2,9.800\n"
            "求める=No.1+2.0"
        )

    if not target_station_text:
        return "求める測点がありません。例: 求める=No.1+2.0"

    points = sorted(points, key=lambda x: x["distance"])

    try:
        target_distance = parse_station(target_station_text, pitch)
    except Exception as e:
        return str(e)

    before_point = None
    after_point = None

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        if p1["distance"] <= target_distance <= p2["distance"]:
            before_point = p1
            after_point = p2
            break

    if before_point is None or after_point is None:
        return "求める測点が、入力した計画高データの範囲外です。"

    d1 = before_point["distance"]
    h1 = before_point["height"]
    d2 = after_point["distance"]
    h2 = after_point["height"]

    if d2 == d1:
        return "同じ距離の測点が重複しています。"

    slope = (h2 - h1) / (d2 - d1)
    target_height = h1 + slope * (target_distance - d1)

    # 返答を短くする
    return f"{target_station_text}　高さ{target_height:.3f}m"


def calculate_simple_average(message):
    """
    以前の簡易平均計算。
    """
    text = message.replace("\n", " ")
    text = text.replace(",", " ")
    text = text.replace("、", " ")

    parts = text.split()
    values = []

    for part in parts:
        try:
            values.append(float(part))
        except ValueError:
            return (
                "入力内容が読み取れません。\n\n"
                "入力例:\n"
                "計画高\n"
                "ピッチ=20\n"
                "No.1,10.000\n"
                "No.2,9.800\n"
                "求める=No.1+2.0"
            )

    if not values:
        return "まだデータがありません。"

    total = sum(values)
    average = total / len(values)

    return (
        f"測定数: {len(values)}点\n"
        f"合計: {total:g}\n"
        f"平均: {average:.3f}"
    )


def calculate_survey_result(message):
    """
    LINEから送られた文字を判定して計算する。
    """

    if not message:
        return "まだデータがありません。"

    text = message.strip()

    if text.startswith("計画高") or text.startswith("中心高") or text.startswith("道路"):
        return calculate_road_center_height(text)

    return calculate_simple_average(text)
