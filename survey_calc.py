import csv
import os
import re


ROAD_PROFILE_CSV = "road_profile.csv"
VERTICAL_CURVE_CSV = "vertical_curve.csv"


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
    必要列:
    station,distance,height
    """
    if not os.path.exists(ROAD_PROFILE_CSV):
        raise FileNotFoundError("road_profile.csv が見つかりません。")

    points = []

    with open(ROAD_PROFILE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {"station", "distance", "height"}
        if not required_columns.issubset(reader.fieldnames):
            raise ValueError("road_profile.csv の見出しは station,distance,height にしてください。")

        for row in reader:
            points.append({
                "station": row["station"].strip(),
                "distance": float(row["distance"]),
                "height": float(row["height"])
            })

    if len(points) < 2:
        raise ValueError("road_profile.csv には最低2点以上のデータが必要です。")

    return sorted(points, key=lambda x: x["distance"])


def load_vertical_curves():
    """
    vertical_curve.csv を読み込む。
    必要列:
    curve_name,bvc_distance,bvc_height,pvi_distance,pvi_height,evc_distance,evc_height
    """
    if not os.path.exists(VERTICAL_CURVE_CSV):
        return []

    curves = []

    with open(VERTICAL_CURVE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "curve_name",
            "bvc_distance",
            "bvc_height",
            "pvi_distance",
            "pvi_height",
            "evc_distance",
            "evc_height"
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "vertical_curve.csv の見出しは "
                "curve_name,bvc_distance,bvc_height,pvi_distance,pvi_height,evc_distance,evc_height "
                "にしてください。"
            )

        for row in reader:
            curves.append({
                "curve_name": row["curve_name"].strip(),
                "bvc_distance": float(row["bvc_distance"]),
                "bvc_height": float(row["bvc_height"]),
                "pvi_distance": float(row["pvi_distance"]),
                "pvi_height": float(row["pvi_height"]),
                "evc_distance": float(row["evc_distance"]),
                "evc_height": float(row["evc_height"])
            })

    return curves


def calculate_vertical_curve_height(distance):
    """
    縦断曲線内ならバーチカル計算を行う。
    曲線外なら None を返す。
    """

    curves = load_vertical_curves()

    for curve in curves:
        bvc_d = curve["bvc_distance"]
        bvc_h = curve["bvc_height"]
        pvi_d = curve["pvi_distance"]
        pvi_h = curve["pvi_height"]
        evc_d = curve["evc_distance"]
        evc_h = curve["evc_height"]

        if bvc_d <= distance <= evc_d:
            if pvi_d == bvc_d or evc_d == pvi_d:
                return None

            # 進入勾配 g1、退出勾配 g2
            g1 = (pvi_h - bvc_h) / (pvi_d - bvc_d)
            g2 = (evc_h - pvi_h) / (evc_d - pvi_d)

            # 縦断曲線長
            L = evc_d - bvc_d
            x = distance - bvc_d

            if L == 0:
                return None

            # 放物線による縦断曲線高
            height = bvc_h + g1 * x + ((g2 - g1) / (2 * L)) * (x ** 2)

            return {
                "height": height,
                "curve_name": curve["curve_name"]
            }

    return None


def calculate_straight_height(distance):
    """
    road_profile.csv から直線補間で高さを計算する。
    """

    points = load_road_profile()

    before_point = None
    after_point = None

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        if p1["distance"] <= distance <= p2["distance"]:
            before_point = p1
            after_point = p2
            break

    if before_point is None or after_point is None:
        return None

    d1 = before_point["distance"]
    h1 = before_point["height"]
    d2 = after_point["distance"]
    h2 = after_point["height"]

    if d2 == d1:
        raise ValueError("road_profile.csv 内に同じ距離のデータがあります。")

    slope = (h2 - h1) / (d2 - d1)
    height = h1 + slope * (distance - d1)

    return height


def calculate_center_height(station_text):
    """
    指定測点の道路計画中心高を計算する。
    先に縦断曲線を確認し、曲線外なら直線補間する。
    """

    distance = parse_station(station_text)

    vertical_result = calculate_vertical_curve_height(distance)

    if vertical_result is not None:
        height = vertical_result["height"]
        return f"{station_text}　高さ{height:.2f}m"

    straight_height = calculate_straight_height(distance)

    if straight_height is None:
        return "入力した測点がCSVデータの範囲外です。"

    return f"{station_text}　高さ{straight_height:.2f}m"


def calculate_survey_result(message):
    """
    LINEから送られた文字を受け取る。
    入力例:
    No.1+2.0
    No.3+5.0
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
            "No.3+5.0\n\n"
            "縦断曲線内は vertical_curve.csv を使って計算します。"
        )

    try:
        return calculate_center_height(text)
    except Exception as e:
        return f"計算できませんでした。\n{str(e)}"
