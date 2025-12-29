# -*- coding: utf-8 -*-
# products.py － 產品資料庫（比例座標版）
#
# 規格：
# - image_base / color_map 建議全小寫，對齊 assets 檔名（例如：cp101_white_front.png）
# - coords 使用「比例座標」：(x_ratio, y_ratio)
#   x_ratio = 0~1（相對於底圖寬度），y_ratio = 0~1（相對於底圖高度）
#
# 例：
#   (0.5, 0.45) = 圖的寬 50% 位置、圖的高 45% 位置

PRODUCT_CATALOG = {
    "團體服系列": {

        # =========================================================
        # CP101 吸濕排汗團體服（比例座標）
        # =========================================================
        "CP101 吸濕排汗團體服": {
            "name": "CP101 吸濕排汗團體服",
            "image_base": "cp101",

            "colors": [
                "白色","淺灰色","深灰色","黑色","粉紅色",
                "玫紅色","紅色","酒紅色","水藍色","湖藍色",
                "寶藍色","藏青色","海藍色","草綠色","墨綠色",
                "卡其色","淺黃色","黃色","淺紫色","深紫色",
                "螢光粉色","螢光橘色","螢光綠色","螢光黃色",
                "奶茶色","蓮藕粉色","玫瑰粉色","瑪瑙紅色",
                "芥末黃色","金色","南瓜橘色","珊瑚橘色",
                "天空藍色","薰衣草色","星空灰色","鯨魚藍色",
                "翡翠綠色","軍綠色","駝色","太妃糖色"
            ],

            # 檔名對應（全小寫）：cp101_<code>_front.png / cp101_<code>_back.png
            "color_map": {
                "白色": "white",
                "淺灰色": "lightgray",
                "深灰色": "darkgray",
                "黑色": "black",
                "粉紅色": "pink",
                "玫紅色": "rose",
                "紅色": "red",
                "酒紅色": "wine",
                "水藍色": "skyblue",
                "湖藍色": "lakeblue",
                "寶藍色": "royalblue",
                "藏青色": "navy",
                "海藍色": "seablue",
                "草綠色": "grassgreen",
                "墨綠色": "darkgreen",
                "卡其色": "khaki",
                "淺黃色": "lightyellow",
                "黃色": "yellow",
                "淺紫色": "lavender",
                "深紫色": "purple",
                "螢光粉色": "neonpink",
                "螢光橘色": "neonorange",
                "螢光綠色": "neongreen",
                "螢光黃色": "neonyellow",
                "奶茶色": "milktea",
                "蓮藕粉色": "lotuspink",
                "玫瑰粉色": "rosepink",
                "瑪瑙紅色": "agate",
                "芥末黃色": "mustard",
                "金色": "gold",
                "南瓜橘色": "pumpkin",
                "珊瑚橘色": "coral",
                "天空藍色": "sky",
                "薰衣草色": "lavenderblue",
                "星空灰色": "spacegray",
                "鯨魚藍色": "whaleblue",
                "翡翠綠色": "emerald",
                "軍綠色": "army",
                "駝色": "camel",
                "太妃糖色": "toffee",
            },

            # ✅ 比例座標（不跑偏）
            # 你原本像素中心大約在 (300,360)（以 600x800 推回比例）
            "pos_front": {
                "正中間 (Center)": {"coords": (0.50, 0.45)},
                "左胸 (Left Chest)": {"coords": (0.37, 0.425)},
                "右胸 (Right Chest)": {"coords": (0.63, 0.425)},
            },
            "pos_back": {
                "背中置中 (Center)": {"coords": (0.50, 0.45)},
                "上背字樣 (Upper Back)": {"coords": (0.50, 0.35)},
            },
        },

        # =========================================================
        # AG21000 重磅棉T（比例座標）
        # =========================================================
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",
            "image_base": "AG21000",

            # 你可依現有庫存再擴充；這裡先放常用色
            "colors": [
                "白色", "黑色", "麻灰", "炭灰 (CharcoalGray)", "深藍 (Navy)",
                "奶茶 (BeigeBrown)"
            ],

            # 檔名對應（建議全小寫）：ag21000_<code>_front.png / ag21000_<code>_back.png
            # main.py 有大小寫容錯，所以就算你 assets 不是全小寫也仍可找到
            "color_map": {
                "白色": "white",
                "黑色": "black",
                "麻灰": "heathergrey",
                "炭灰 (CharcoalGray)": "charcoalgray",
                "深藍 (Navy)": "navy",
                "奶茶 (BeigeBrown)": "beigebrown",
            },

            # ✅ 比例座標（通用穩定點位）
            # 若你想更精準貼合某款版型，可再微調比例值（但不會再因底圖尺寸而跑掉）
            "pos_front": {
                "正中間 (Center)": {"coords": (0.50, 0.52)},
                "左胸 (Left Chest)": {"coords": (0.38, 0.40)},
                "右胸 (Right Chest)": {"coords": (0.62, 0.40)},
                "左臂 (Left Sleeve)": {"coords": (0.18, 0.36)},
                "右臂 (Right Sleeve)": {"coords": (0.82, 0.36)},
            },
            "pos_back": {
                "背中置中 (Center)": {"coords": (0.50, 0.52)},
                "上背字樣 (Upper Back)": {"coords": (0.50, 0.33)},
                # ✅ 給 main.py 的 SLEEVE_MAPPING 用（正面袖口要投到背面袖口時會找這兩個 key）
                "左臂-後 (L.Sleeve Back)": {"coords": (0.18, 0.36)},
                "右臂-後 (R.Sleeve Back)": {"coords": (0.82, 0.36)},
            },
        },
    }
}

