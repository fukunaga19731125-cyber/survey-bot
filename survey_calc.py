import csv
import os
import re


ROAD_PROFILE_CSV = "road_profile.csv"
VERTICAL_CURVE_CSV = "vertical_curve.csv"
CROSS_SECTION_CSV = "cross_section.csv"

# 通常の表示小数桁
DEFAULT_DECIMALS = 3


def normalize_text(text):
    """
    全角・表記ゆれを整える。
    """
    text = str(text).strip()
    text = text.replace("Ｎｏ", "No")
    text = text.replace("ｎｏ", "No")
    text = text.replace("NO", "No")
    text = text.replace("no", "No")
    text = text.replace("＋", "+")
    text = text.replace("．", ".")
    text = text.replace("＝", "=")
    text = text.replace("，", ",")
    text = text.replace("　", " ")
    return text


def parse_station(station_text, pitch=20.0):
    """
    測点文字を距離に変換する。
    例:
    No.1       -> 20.0
    No.1+2.0   -> 22.0
    """
    text = normalize_text(station_text)

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
    No.3+5 右
    横断 No.3+5
    """
    text = normalize_text(message)

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
    text = normalize_text(message)

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


def extract_side(message):
    """
    左右指定を取得する。
    戻り値:
    "left", "right", None
    """
    text = normalize_text(message)

    if "左" in text:
        return "left"

    if "右" in text:
        return "right"

    return None


def to_float(value_text):
    """
    m、％、空白などを除去して数値化する。
    """
    text = str(value_text).strip()
    text = text.replace("ｍ", "")
    text = text.replace("m", "")
    text = text.replace("Ｍ", "")
    text = text.replace("M", "")
    text = text.replace("％", "")
    text = text.replace("%", "")
    text = text.replace(",", "")
    text = text.strip()

    return float(text)


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
                "distance": to_float(distance_text),
                "height": to_float(height_text)
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

            pvi_distance = to_float(pvi_distance_text)
            pvi_height = to_float(pvi_height_text)
            curve_length = to_float(curve_length_text)
            g1_percent = to_float(g1_percent_text)
            g2_percent = to_float(g2_percent_text)

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


def load_cross_sections():
    """
    cross_section.csv を読み込む。
    必要列:
    section_name,start_station,start_distance,end_station,end_distance,
    left_width,left_slope,right_width,right_slope
    """
    if not os.path.exists(CROSS_SECTION_CSV):
        raise FileNotFoundError("cross_section.csv が見つかりません。")

    sections = []

    with open(CROSS_SECTION_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "section_name",
            "start_station",
            "start_distance",
            "end_station",
            "end_distance",
            "left_width",
            "left_slope",
            "right_width",
            "right_slope"
        }

        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "cross_section.csv の見出しは "
                "section_name,start_station,start_distance,end_station,end_distance,"
                "left_width,left_slope,right_width,right_slope にしてください。"
            )

        for row in reader:
            section_name = row.get("section_name", "").strip()
            start_station = row.get("start_station", "").strip()
            start_distance_text = row.get("start_distance", "").strip()
            end_station = row.get("end_station", "").strip()
            end_distance_text = row.get("end_distance", "").strip()
            left_width_text = row.get("left_width", "").strip()
            left_slope_text = row.get("left_slope", "").strip()
            right_width_text = row.get("right_width", "").strip()
            right_slope_text = row.get("right_slope", "").strip()

            # 空白行は無視
            if (
                not section_name
                and not start_station
                and not start_distance_text
                and not end_station
                and not end_distance_text
                and not left_width_text
                and not left_slope_text
                and not right_width_text
                and not right_slope_text
            ):
                continue

            if not end_distance_text:
                raise ValueError(f"{section_name} の end_distance が空白です。")

            section = {
                "section_name": section_name,
                "start_station": start_station,
                "start_distance": to_float(start_distance_text),
                "end_station": end_station,
                "end_distance": to_float(end_distance_text),
                "left_width": to_float(left_width_text),
                "left_slope": to_float(left_slope_text),
                "right_width": to_float(right_width_text),
                "right_slope": to_float(right_slope_text),
                "memo": str(row.get("memo", "") or "").strip()
            }

            if section["end_distance"] < section["start_distance"]:
                raise ValueError(f"{section_name} の終了距離が開始距離より小さいです。")

            sections.append(section)

    if not sections:
        raise ValueError("cross_section.csv に横断データがありません。")

    return sorted(sections, key=lambda x: x["start_distance"])


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


def get_center_height_result(station_text):
    """
    測点から道路中心高を取得する。
    縦断曲線内なら縦断曲線を優先。
    曲線外なら直線補間。
    """
    distance = parse_station(station_text)

    vertical_result = calculate_vertical_curve_height(distance)

    if vertical_result is not None:
        return {
            "station": station_text,
            "distance": distance,
            "height": vertical_result["height"],
            "method": vertical_result["method"]
        }

    straight_result = calculate_straight_height(distance)

    if straight_result is None:
        points = load_road_profile()
        first = points[0]
        last = points[-1]

        raise ValueError(
            "入力した測点がCSVデータの範囲外です。\n"
            f"登録範囲：{first['station']} ～ {last['station']}"
        )

    return {
        "station": station_text,
        "distance": distance,
        "height": straight_result["height"],
        "method": straight_result["method"]
    }


def find_cross_section(distance):
    """
    指定距離が入る横断設計区間を探す。
    """
    sections = load_cross_sections()

    for section in sections:
        start_d = section["start_distance"]
        end_d = section["end_distance"]

        # 境界上の重複を避けるため、最後以外は start <= x < end
        if start_d <= distance < end_d:
            return section

    # 最終点ぴったりの場合の救済
    last = sections[-1]
    if abs(distance - last["end_distance"]) < 0.0001:
        return last

    first = sections[0]
    last = sections[-1]

    raise ValueError(
        "入力した測点が横断設計データの範囲外です。\n"
        f"横断登録範囲：{first['start_station']} ～ {last['end_station']}"
    )


def calculate_center_height(message):
    """
    中心高のみを返す。
    """
    station_text = extract_station_text(message)
    decimals = extract_decimals(message)

    result = get_center_height_result(station_text)

    return (
        f"{station_text}　高さ{result['height']:.{decimals}f}m\n"
        f"{result['method']}"
    )


def calculate_side_height(message):
    """
    No.3+5 右
    No.3+5 左
    のような入力から、左右どちらかの端部高さを返す。
    """
    station_text = extract_station_text(message)
    side = extract_side(message)
    decimals = extract_decimals(message)

    if side not in ["left", "right"]:
        raise ValueError("左または右を指定してください。例: No.3+5 右")

    center_result = get_center_height_result(station_text)
    center_height = center_result["height"]
    distance = center_result["distance"]

    section = find_cross_section(distance)

    if side == "right":
        width = section["right_width"]
        slope = section["right_slope"]
        side_label = "右"
    else:
        width = section["left_width"]
        slope = section["left_slope"]
        side_label = "左"

    side_height = center_height + width * (slope / 100)

    return (
        f"{station_text} {side_label}\n"
        f"高さ{side_height:.{decimals}f}m\n"
        f"勾配{slope:.3f}%\n"
        f"{side_label}{width:.3f}m\n"
        f"{center_result['method']}"
    )


def calculate_cross_both(message):
    """
    横断 No.3+5
    のような入力で左右両方を返す。
    """
    station_text = extract_station_text(message)
    decimals = extract_decimals(message)

    center_result = get_center_height_result(station_text)
    center_height = center_result["height"]
    distance = center_result["distance"]

    section = find_cross_section(distance)

    left_height = center_height + section["left_width"] * (section["left_slope"] / 100)
    right_height = center_height + section["right_width"] * (section["right_slope"] / 100)

    return (
        f"{station_text}\n"
        f"中心高{center_height:.{decimals}f}m\n"
        f"左端{left_height:.{decimals}f}m\n"
        f"右端{right_height:.{decimals}f}m\n"
        f"{center_result['method']}"
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

    # cross_section.csv の確認
    if os.path.exists(CROSS_SECTION_CSV):
        sections = load_cross_sections()
        first_section = sections[0]
        last_section = sections[-1]

        message += (
            "\n\n"
            f"cross_section：{len(sections)}区間\n"
            f"横断範囲：{first_section['start_station']} ～ {last_section['end_station']}"
        )
    else:
        message += "\n\ncross_section：未登録"

    return message


def calculate_survey_result(message):
    """
    LINEから送られた文字を受け取る。
    入力例:
    No.3+5
    No.3+5 右
    No.3+5 左
    横断 No.3+5
    データ確認
    """
    if not message:
        return "測点を入力してください。例: No.1+2.0"

    text = normalize_text(message)

    if text in ["使い方", "ヘルプ", "help"]:
        return (
            "道路計画中心高・横断高さを計算します。\n\n"
            "中心高:\n"
            "No.3+5\n\n"
            "右端高さ:\n"
            "No.3+5 右\n\n"
            "左端高さ:\n"
            "No.3+5 左\n\n"
            "左右両方:\n"
            "横断 No.3+5\n\n"
            "小数桁指定:\n"
            "No.3+5 右 小数3\n\n"
            "データ確認 と送るとCSVの読込状況を確認できます。"
        )

    if text in ["データ確認", "データ", "確認"]:
        try:
            return check_data_status()
        except Exception as e:
            return f"データ確認できませんでした。\n{str(e)}"

    # 横断 No.3+5 → 左右両方
    if text.startswith("横断"):
        try:
            return calculate_cross_both(text)
        except Exception as e:
            return f"横断計算できませんでした。\n{str(e)}"

    # No.3+5 右 / No.3+5 左 → 片側
    if "右" in text or "左" in text:
        try:
            return calculate_side_height(text)
        except Exception as e:
            return f"横断計算できませんでした。\n{str(e)}"

    # それ以外は中心高
    try:
        return calculate_center_height(text)
    except Exception as e:
        return f"計算できませんでした。\n{str(e)}"
