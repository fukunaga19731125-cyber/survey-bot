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
    新しい形式:
    curve_name,pvi_station,pvi_distance,pvi_height,curve_length,g1_percent,g2_percent,curve_radius,memo

    pvi_height は、バーチカル補正前の勾配変化点高。
    g1_percent は進入勾配。
    g2_percent は退出勾配。
    curve_radius は確認用。計算には使わない。
    """
    if not os.path.exists(VERTICAL_CURVE_CSV):
        return []

    curves = []

    with open(VERTICAL_CURVE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "curve_name",
            "pvi_station",
            "pvi_distance",
            "pvi_height",
            "curve_length",
            "g1_percent",
            "g2_percent"
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "vertical_curve.csv の見出しは、最低限 "
                "curve_name,pvi_station,pvi_distance,pvi_height,curve_length,g1_percent,g2_percent "
                "にしてください。"
            )

        for row in reader:
            curve_name = row["curve_name"].strip()
            pvi_station = row["pvi_station"].strip()
            pvi_distance = float(row["pvi_distance"])
            pvi_height = float(row["pvi_height"])
            curve_length = float(row["curve_length"])
            g1_percent = float(row["g1_percent"])
            g2_percent = float(row["g2_percent"])

            curve_radius = ""
            if "curve_radius" in row and row["curve_radius"] is not None:
                curve_radius = row["curve_radius"].strip()

            memo = ""
            if "memo" in row and row["memo"] is not None:
                memo = row["memo"].strip()

            if curve_length <= 0:
                raise ValueError(f"{curve_name} の曲線長が0以下です。")

            # PVIを中心としてBVC・EVCを計算
            bvc_distance = pvi_distance - curve_length / 2
            evc_distance = pvi_distance + curve_length / 2

            # 勾配%を小数勾配に変換
            g1 = g1_percent / 100
            g2 = g2_percent / 100

            # BVC・EVCの接線上高さを計算
            # pvi_height は接線交点高
            bvc_height = pvi_height - g1 * (curve_length / 2)
            evc_height = pvi_height + g2 * (curve_length / 2)

            curves.append({
                "curve_name": curve_name,
                "pvi_station": pvi_station,
                "pvi_distance": pvi_distance,
                "pvi_height": pvi_height,
                "curve_length": curve_length,
                "g1_percent": g1_percent,
                "g2_percent": g2_percent,
                "g1": g1,
                "g2": g2,
                "bvc_distance": bvc_distance,
                "bvc_height": bvc_height,
                "evc_distance": evc_distance,
                "evc_height": evc_height,
                "curve_radius": curve_radius,
                "memo": memo
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
        evc_d = curve["evc_distance"]
        g1 = curve["g1"]
        g2 = curve["g2"]
        L = curve["curve_length"]

        if bvc_d <= distance <= evc_d:
            x = distance - bvc_d

            # 放物線縦断曲線
            # 高さ = BVC高 + g1*x + ((g2-g1)/(2L))*x^2
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
