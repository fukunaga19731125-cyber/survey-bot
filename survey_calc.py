import csv
import os
import re


CSV_FILE = "road_profile.csv"


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
        raise ValueError("測点の形式が読み取れません。例: No.1+2.0")

    no_number = int(match.group(1))
    plus_value = float(match.group(2)) if match.group(2) else 0.0

    return no_number * pitch + plus_value


def load_road_profile():
    """
    road_profile.csv を読み込む。
    必要な列:
    station,distance,height
    """
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError("road_profile.csv が見つかりません。GitHubに追加してください。")

    points = []

    with open(CSV_FILE, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {"station", "distance", "height"}
        if not required_columns.issubset(reader.fieldnames):
            raise ValueError("CSVの見出しは station,distance,height にしてください。")

        for row in reader:
            station = row["station"].strip()
            distance = float(row["distance"])
            height = float(row["height"])

            points.append({
                "station": station,
                "distance": distance,
                "height": height
            })

    if len(points) < 2:
        raise ValueError("CSVには最低2点以上のデータが必要です。")

    points = sorted(points, key=lambda x: x["distance"])
    return points


def calculate_center_height(target_station_text):
    """
    CSVの道路中心高データから、指定測点の高さを計算する。
    """
    points = load_road_profile()

    # 基本は20mピッチ
    pitch = 20.0
    target_distance = parse_station(target_station_text, pitch)

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
        return "入力した測点がCSVデータの範囲外です。"

    d1 = before_point["distance"]
    h1 = before_point["height"]
    d2 = after_point["distance"]
    h2 = after_point["height"]

    if d2 == d1:
        return "CSV内に同じ距離のデータがあります。確認してください。"

    slope = (h2 - h1) / (d2 - d1)
    target_height = h1 + slope * (target_distance - d1)

    return f"{target_station_text}　高さ{target_height:.2f}m"


def calculate_survey_result(message):
    """
    LINEから送られた文字を受け取る。
    入力例:
    No.1+2.0
    No.2+5.5
    使い方
    """

    if not message:
        return "測点を入力してください。例: No.1+2.0"

    text = message.strip()

    if text in ["使い方", "ヘルプ", "help"]:
        return (
            "道路計画中心高を計算します。\n\n"
            "入力例:\n"
            "No.1+2.0\n"
            "No.2+5.5\n\n"
            "CSVは road_profile.csv を使用します。"
        )

    try:
        return calculate_center_height(text)
    except Exception as e:
        return f"計算できませんでした。\n{str(e)}"
