import csv
import os
import re


ROAD_PROFILE_CSV = "road_profile.csv"
VERTICAL_CURVE_CSV = "vertical_curve.csv"
CROSS_SECTION_CSV = "cross_section.csv"
HORIZONTAL_CURVE_CSV = "horizontal_curve.csv"

DEFAULT_DECIMALS = 3


def normalize_text(text):
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


def get_value(row, names, default=""):
    """
    CSVの列名を日本語・英語どちらでも読めるようにする。
    """
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name]).strip()
    return default


def to_float(value_text):
    """
    m、％、カンマなどを除去して数値化する。
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

    if text == "":
        raise ValueError("数値欄に空白があります。CSVを確認してください。")

    return float(text)


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
    """
    text = normalize_text(message)

    if "左" in text:
        return "left"

    if "右" in text:
        return "right"

    return None


def load_road_profile():
    """
    road_profile.csv

    日本語列名:
    測点,距離,計画中心高

    英語列名:
    station,distance,height
    """
    if not os.path.exists(ROAD_PROFILE_CSV):
        raise FileNotFoundError("road_profile.csv が見つかりません。")

    points = []

    with open(ROAD_PROFILE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            station = get_value(row, ["測点", "station"])
            distance_text = get_value(row, ["距離", "distance"])
            height_text = get_value(row, ["計画中心高", "中心高", "height"])

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
    vertical_curve.csv

    日本語列名:
    曲線名,変化点測点,変化点距離,変化点高,曲線長,進入勾配,退出勾配,曲線半径,メモ

    英語列名:
    curve_name,pvi_station,pvi_distance,pvi_height,curve_length,g1_percent,g2_percent,curve_radius,memo
    """
    if not os.path.exists(VERTICAL_CURVE_CSV):
        return []

    curves = []

    with open(VERTICAL_CURVE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            curve_name = get_value(row, ["曲線名", "curve_name"])
            pvi_station = get_value(row, ["変化点測点", "pvi_station"])
            pvi_distance_text = get_value(row, ["変化点距離", "pvi_distance"])
            pvi_height_text = get_value(row, ["変化点高", "pvi_height"])
            curve_length_text = get_value(row, ["曲線長", "curve_length"])
            g1_percent_text = get_value(row, ["進入勾配", "g1_percent"])
            g2_percent_text = get_value(row, ["退出勾配", "g2_percent"])

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

            curve_radius = get_value(row, ["曲線半径", "curve_radius"])
            memo = get_value(row, ["メモ", "memo"])

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
    cross_section.csv

    日本語列名:
    区間名,開始測点,開始距離,終了測点,終了距離,左幅,左勾配,右幅,右勾配,メモ

    英語列名:
    section_name,start_station,start_distance,end_station,end_distance,left_width,left_slope,right_width,right_slope,memo
    """
    if not os.path.exists(CROSS_SECTION_CSV):
        raise FileNotFoundError("cross_section.csv が見つかりません。")

    sections = []

    with open(CROSS_SECTION_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            section_name = get_value(row, ["区間名", "section_name"])
            start_station = get_value(row, ["開始測点", "start_station"])
            start_distance_text = get_value(row, ["開始距離", "start_distance"])
            end_station = get_value(row, ["終了測点", "end_station"])
            end_distance_text = get_value(row, ["終了距離", "end_distance"])
            left_width_text = get_value(row, ["左幅", "left_width"])
            left_slope_text = get_value(row, ["左勾配", "left_slope"])
            right_width_text = get_value(row, ["右幅", "right_width"])
            right_slope_text = get_value(row, ["右勾配", "right_slope"])

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
                "memo": get_value(row, ["メモ", "memo"])
            }

            if section["end_distance"] < section["start_distance"]:
                raise ValueError(f"{section_name} の終了距離が開始距離より小さいです。")

            sections.append(section)

    if not sections:
        raise ValueError("cross_section.csv に横断データがありません。")

    return sorted(sections, key=lambda x: x["start_distance"])


def load_horizontal_curves():
    """
    horizontal_curve.csv

    日本語列名:
    曲線名,BC測点,BC距離,EC測点,EC距離,半径,方向,左幅,左勾配,右幅,右勾配,メモ

    英語列名:
    curve_name,bc_station,bc_distance,ec_station,ec_distance,radius,direction,left_width,left_slope,right_width,right_slope,memo
    """
    if not os.path.exists(HORIZONTAL_CURVE_CSV):
        return []

    curves = []

    with open(HORIZONTAL_CURVE_CSV, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            curve_name = get_value(row, ["曲線名", "curve_name"])
            bc_station = get_value(row, ["BC測点", "bc_station"])
            bc_distance_text = get_value(row, ["BC距離", "bc_distance"])
            ec_station = get_value(row, ["EC測点", "ec_station"])
            ec_distance_text = get_value(row, ["EC距離", "ec_distance"])
            radius_text = get_value(row, ["半径", "radius"])
            direction = get_value(row, ["方向", "direction"])
            left_width_text = get_value(row, ["左幅", "left_width"])
            left_slope_text = get_value(row, ["左勾配", "left_slope"])
            right_width_text = get_value(row, ["右幅", "right_width"])
            right_slope_text = get_value(row, ["右勾配", "right_slope"])

            # 空白行は無視
            if (
                not curve_name
                and not bc_station
                and not bc_distance_text
                and not ec_station
                and not ec_distance_text
                and not left_width_text
                and not left_slope_text
                and not right_width_text
                and not right_slope_text
            ):
                continue

            curve = {
                "curve_name": curve_name,
                "bc_station": bc_station,
                "bc_distance": to_float(bc_distance_text),
                "ec_station": ec_station,
                "ec_distance": to_float(ec_distance_text),
                "radius": to_float(radius_text) if radius_text else 0.0,
                "direction": direction,
                "left_width": to_float(left_width_text),
                "left_slope": to_float(left_slope_text),
                "right_width": to_float(right_width_text),
                "right_slope": to_float(right_slope_text),
                "memo": get_value(row, ["メモ", "memo"])
            }

            if curve["ec_distance"] < curve["bc_distance"]:
                raise ValueError(f"{curve_name} のEC距離がBC距離より小さいです。")

            curves.append(curve)

    return sorted(curves, key=lambda x: x["bc_distance"])


def calculate_vertical_curve_height(distance):
    """
    縦断曲線内ならバーチカル計算。
    曲線外なら None。
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
            height = bvc_h + g1 * x + ((g2 - g1) / (2 * L)) * (x ** 2)

            return {
                "height": height,
                "method": "縦断：曲線区間",
                "curve_name": curve["curve_name"]
            }

    return None


def calculate_straight_height(distance):
    """
    road_profile.csv から直線補間で高さを計算。
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
        "method": "縦断：直線区間",
        "before_point": before_point,
        "after_point": after_point
    }


def get_center_height_result(station_text):
    """
    測点から道路中心高を取得。
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
            "vertical_status": vertical_result["method"]
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
        "vertical_status": straight_result["method"]
    }


def find_cross_section(distance):
    """
    通常横断区間を探す。
    """
    sections = load_cross_sections()

    for section in sections:
        if section["start_distance"] <= distance < section["end_distance"]:
            return section

    last = sections[-1]
    if abs(distance - last["end_distance"]) < 0.0001:
        return last

    first = sections[0]
    raise ValueError(
        "入力した測点が横断設計データの範囲外です。\n"
        f"横断登録範囲：{first['start_station']} ～ {last['end_station']}"
    )


def find_horizontal_curve(distance):
    """
    平面曲線内なら曲線データを返す。
    クロソイドなしなので BC距離 <= 測点距離 <= EC距離 で判定。
    """
    curves = load_horizontal_curves()

    for curve in curves:
        if curve["bc_distance"] <= distance <= curve["ec_distance"]:
            return curve

    return None


def get_alignment_status(distance, vertical_status):
    """
    平面・縦断の区間種別を返す。
    """
    horizontal_curve = find_horizontal_curve(distance)

    if horizontal_curve is not None:
        plane_status = "平面：曲線区間"
    else:
        plane_status = "平面：直線区間"

    return plane_status, vertical_status


def get_cross_condition(distance):
    """
    横断条件の優先順位:
    1. 平面曲線 horizontal_curve.csv
    2. 通常横断 cross_section.csv
    """
    horizontal_curve = find_horizontal_curve(distance)

    if horizontal_curve is not None:
        return {
            "source": "horizontal",
            "plane_status": "平面：曲線区間",
            "left_width": horizontal_curve["left_width"],
            "left_slope": horizontal_curve["left_slope"],
            "right_width": horizontal_curve["right_width"],
            "right_slope": horizontal_curve["right_slope"],
            "curve_name": horizontal_curve["curve_name"]
        }

    section = find_cross_section(distance)

    return {
        "source": "cross",
        "plane_status": "平面：直線区間",
        "left_width": section["left_width"],
        "left_slope": section["left_slope"],
        "right_width": section["right_width"],
        "right_slope": section["right_slope"],
        "section_name": section["section_name"]
    }


def calculate_center_height(message):
    """
    中心高のみを返す。
    """
    station_text = extract_station_text(message)
    decimals = extract_decimals(message)

    result = get_center_height_result(station_text)

    plane_status, vertical_status = get_alignment_status(
        result["distance"],
        result["vertical_status"]
    )

    return (
        f"{station_text}　高さ{result['height']:.{decimals}f}m\n"
        f"{plane_status}\n"
        f"{vertical_status}"
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

    condition = get_cross_condition(distance)

    if side == "right":
        width = condition["right_width"]
        slope = condition["right_slope"]
        side_label = "右"
    else:
        width = condition["left_width"]
        slope = condition["left_slope"]
        side_label = "左"

    side_height = center_height + width * (slope / 100)

    plane_status, vertical_status = get_alignment_status(
        distance,
        center_result["vertical_status"]
    )

    return (
        f"{station_text} {side_label}\n"
        f"高さ{side_height:.{decimals}f}m\n"
        f"勾配{slope:.3f}%\n"
        f"{side_label}{width:.3f}m\n"
        f"{plane_status}\n"
        f"{vertical_status}"
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

    condition = get_cross_condition(distance)

    left_height = center_height + condition["left_width"] * (condition["left_slope"] / 100)
    right_height = center_height + condition["right_width"] * (condition["right_slope"] / 100)

    plane_status, vertical_status = get_alignment_status(
        distance,
        center_result["vertical_status"]
    )

    return (
        f"{station_text}\n"
        f"中心高{center_height:.{decimals}f}m\n"
        f"左端{left_height:.{decimals}f}m\n"
        f"右端{right_height:.{decimals}f}m\n"
        f"{plane_status}\n"
        f"{vertical_status}"
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

    message = (
        "データ確認\n\n"
        f"road_profile：{len(road_points)}点\n"
        f"登録範囲：{first_point['station']} ～ {last_point['station']}\n\n"
        f"vertical_curve：{len(vertical_curves)}曲線"
    )

    if len(vertical_curves) > 0:
        curve_lines = []
        for curve in vertical_curves:
            bvc_station = format_station_from_distance(curve["bvc_distance"])
            evc_station = format_station_from_distance(curve["evc_distance"])
            curve_lines.append(f"{curve['curve_name']}：{bvc_station} ～ {evc_station}")

        message += "\n" + "\n".join(curve_lines)

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

    if os.path.exists(HORIZONTAL_CURVE_CSV):
        horizontal_curves = load_horizontal_curves()
        message += f"\n\nhorizontal_curve：{len(horizontal_curves)}曲線"

        if len(horizontal_curves) > 0:
            curve_lines = []
            for curve in horizontal_curves:
                curve_lines.append(
                    f"{curve['curve_name']}：{curve['bc_station']} ～ {curve['ec_station']}"
                )
            message += "\n" + "\n".join(curve_lines)
    else:
        message += "\n\nhorizontal_curve：未登録"

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

    if text.startswith("横断"):
        try:
            return calculate_cross_both(text)
        except Exception as e:
            return f"横断計算できませんでした。\n{str(e)}"

    if "右" in text or "左" in text:
        try:
            return calculate_side_height(text)
        except Exception as e:
            return f"横断計算できませんでした。\n{str(e)}"

    try:
        return calculate_center_height(text)
    except Exception as e:
        return f"計算できませんでした。\n{str(e)}"
