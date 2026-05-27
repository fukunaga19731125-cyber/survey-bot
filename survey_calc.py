import csv
import os
import re


ROAD_PROFILE_CSV = "road_profile.csv"
VERTICAL_CURVE_CSV = "vertical_curve.csv"

# 通常の表示小数桁
DEFAULT_DECIMALS = 2


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


def format_station_from_distance(distance, pitch=20.0):
    """
    距離から測点表示を作る。
    例:
    65.0 -> No.3+5
    """
    no_number = int(distance // pitch)
    plus_value = distance - no_number * pitch

    if abs(plus_value) < 0.0001:
        return f"No.{no_number}"

    plus_text = f"{plus_value:.3f}".rstrip("0").rstrip(".")
    return f"No.{no_number}+{plus_text}"


def extract_station_text(message):
    """
    LINEメッセージ内から No.○+○ を抜き出す。
    例:
    No.3+5
    No.3+5 小数3
    """
    text = message.strip()
    text = text.replace("Ｎｏ", "No")
    text = text.replace("ｎｏ", "No")
    text = text.replace("NO", "No")
    text = text.replace("no", "No")
    text = text.replace("＋", "+")
    text = text.replace("．", ".")

    pattern = r"No\.?\s*\d+(?:\+[0-9.]+)?"
    match = re.search(pattern, text)

    if not match:
        raise ValueError("測点の形式が読み取れません。例: No.1+2.0")

    station = match.group(0)
    station = station.replace(" ", "")
    return station


def extract_decimals(message):
    """
    小数桁をメッセージから取得する。
    例:
    No.3+5 小数3
    No.3+5 小数=3
    No.3+5 桁3
    """
    text = message.strip()
    text = text.replace("＝", "=")

    patterns = [
        r"小数\s*=?\s*(\d+)",
        r"桁\s*=?\s*(\d+)",
        r"(\d+)\s*桁"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            decimals = int(match.group(1))

            if decimals < 0:
                decimals = 0
            if decimals > 4:
                decimals = 4

            return decimals

    return DEFAULT_DECIMALS


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
        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError("road_profile.csv の見出しは station,distance,height にしてください。")

        for row in reader:
            station = row.get("station", "").strip()
            distance_text = row.get("distance", "").strip()
            height_text = row.get("height", "").strip()

            # 空白行は無視
            if not station and not distance_text and not height_text:
                continue

            points.append({
                "station": station,
                "distance": float(distance_text),
                "height": float(height_text)
            })

    if len(points) < 2:
        raise ValueError("road_profile.csv には最低2点以上のデータが必要です。")

    return sorted(points, key=lambda x: x["distance"])


def load_vertical_curves():
    """
    vertical_curve.csv を読み込む。
    必要列:
    curve_name,pvi_station,pvi_distance,pvi_height,curve_length,g1_percent,g2_percent
    任意列:
    curve_radius,memo
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

        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "vertical_curve.csv の見出しは、最低限 "
                "curve_name,pvi_station,pvi_distance,pvi_height,curve_length,g1_percent,g2_percent "
                "にしてください。"
            )

        for row in reader:
            curve_name = row.get("curve_name", "").strip()
            pvi_station = row.get("pvi_station", "").strip()
            pvi_distance_text = row.get("pvi_distance", "").strip()
            pvi_height_text = row.get("pvi_height", "").strip()
            curve_length_text = row.get("curve_length", "").strip()
            g1_percent_text = row.get("g1_percent", "").strip()
            g2_percent_text = row.get("g2_percent", "").strip()

            # 空白行は無視
            if (
                not curve_name
                and not pvi_station
                and not pvi_distance_text
                and not pvi_height_text
                and not curve_length_text
                and not g1_percent_text
                and not g2_percent_text
            ):
                continue

            pvi_distance = float(pvi_distance_text)
            pvi_height = float(pvi_height_text)
            curve_length = float(curve_length_text)
            g1_percent = float(g1_percent_text)
            g2_percent = float(g2_percent_text)

            if curve_length <= 0:
                raise ValueError(f"{curve_name} の曲線長が0以下です。")

            curve_radius = row.get("curve_radius", "")
            if curve_radius is None:
                curve_radius = ""
            curve_radius = str(curve_radius).strip()

            memo = row.get("memo", "")
            if memo is None:
                memo = ""
            memo = str(memo).strip()

            # PVIを中心としてBVC・EVCを計算
            bvc_distance = pvi_distance - curve_length / 2
            evc_distance = pvi_distance + curve_length / 2

            # 勾配%を小数勾配に変換
            g1 = g1_percent / 100
            g2 = g2_percent / 100

            # PVI高はバーチカル補正前の接線交点高
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
            height = bvc_h + g1 * x + ((g2 - g1) / (2 * L)) * (x ** 2)

            return {
                "height": height,
                "method": f"縦断曲線 {curve['curve_name']}",
                "curve": curve
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

    return {
        "height": height,
        "method": "直線補間",
        "before_point": before_point,
        "after_point": after_point
    }


def calculate_center_height(message):
    """
    指定測点の道路計画中心高を計算する。
    縦断曲線内なら縦断曲線を優先。
    曲線外なら直線補間。
    """
    station_text = extract_station_text(message)
    decimals = extract_decimals(message)
    distance = parse_station(station_text)

    vertical_result = calculate_vertical_curve_height(distance)

    if vertical_result is not None:
        height = vertical_result["height"]
        method = vertical_result["method"]

        return (
            f"{station_text}　高さ{height:.{decimals}f}m\n"
            f"{method}"
        )

    straight_result = calculate_straight_height(distance)

    if straight_result is None:
        points = load_road_profile()
        first = points[0]
        last = points[-1]

        return (
            "入力した測点がCSVデータの範囲外です。\n"
            f"登録範囲：{first['station']} ～ {last['station']}"
        )

    height = straight_result["height"]
    method = straight_result["method"]

    return (
        f"{station_text}　高さ{height:.{decimals}f}m\n"
        f"{method}"
    )


def check_data_status():
    """
    CSVデータ確認用。
    LINEで「データ確認」と送る。
    """
    road_points = load_road_profile()
    vertical_curves = load_vertical_curves()

    first_point = road_points[0]
    last_point = road_points[-1]

    road_count = len(road_points)
    curve_count = len(vertical_curves)

    message = (
        "データ確認\n\n"
        f"road_profile：{road_count}点\n"
        f"登録範囲：{first_point['station']} ～ {last_point['station']}\n\n"
        f"vertical_curve：{curve_count}曲線"
    )

    if curve_count > 0:
        curve_lines = []

        for curve in vertical_curves:
            bvc_station = format_station_from_distance(curve["bvc_distance"])
            evc_station = format_station_from_distance(curve["evc_distance"])

            curve_lines.append(
                f"{curve['curve_name']}：{bvc_station} ～ {evc_station}"
            )

        message += "\n" + "\n".join(curve_lines)

    return message


def calculate_survey_result(message):
    """
    LINEから送られた文字を受け取る。
    入力例:
    No.1+2.0
    No.3+5 小数3
    データ確認
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
            "No.3+5\n"
            "No.3+5 小数3\n\n"
            "データ確認 と送るとCSVの読込状況を確認できます。"
        )

    if text in ["データ確認", "データ", "確認"]:
        try:
            return check_data_status()
        except Exception as e:
            return f"データ確認できませんでした。\n{str(e)}"

    try:
        return calculate_center_height(text)
    except Exception as e:
        return f"計算できませんでした。\n{str(e)}"
