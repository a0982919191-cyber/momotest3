# -*- coding: utf-8 -*-
# products.py － 產品資料庫（比例座標版，已修正左右胸/袖口/背面需求）

PRODUCT_CATALOG = {
    "團體服系列": {

        # =========================================================
        # CP101 吸濕排汗團體服（比例座標）
        # - 修正：左胸/右胸以「穿者視角」定義（畫面左右會相反）
        # - 檔名：cp101_<code>_front.png / cp101_<code>_back.png（你目前 assets 是全小寫）
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

            # 全小寫對齊你 assets：cp101_*.png
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

            # ✅ 比例座標
            "pos_front": {
                "正中間 (Center)": {"coords": (0.50, 0.45)},
                # ✅ 修正：以「穿者視角」=> 左胸在畫面右側、右胸在畫面左側
                "左胸 (Left Chest)": {"coords": (0.63, 0.425)},
                "右胸 (Right Chest)": {"coords": (0.37, 0.425)},
            },

            "pos_back": {
                "背中置中 (Center)": {"coords": (0.50, 0.45)},
                "上背字樣 (Upper Back)": {"coords": (0.50, 0.35)},
            },
        },

        # =========================================================
        # AG21000 重磅棉T（比例座標）
        # - 修正：衣服找不到 => image_base / color_map 改成「跟你 assets 檔名一致」
        # - 修正：左臂/右臂補回來（只在正面選）
        # - 背面只保留：背中置中 + 袖口延續用的「左臂-後/右臂-後」
        # =========================================================
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",

            # ✅ 這裡請務必與你的檔名一致：
            #   AG21000_CharcoalGray_front.png
            "image_base": "AG21000",

            "colors": [
                "白色",
                "黑色",
                "麻灰",
                "炭灰 (CharcoalGray)",
                "深藍 (Navy)",
                "奶茶 (BeigeBrown)",
            ],

            # ✅ 這裡也請務必與 assets 檔名一致（CamelCase）
            "color_map": {
                "白色": "White",
                "黑色": "Black",
                "麻灰": "HeatherGrey",
                "炭灰 (CharcoalGray)": "CharcoalGray",
                "深藍 (Navy)": "Navy",
                "奶茶 (BeigeBrown)": "BeigeBrown",
            },

            "pos_front": {
                "正中間 (Center)": {"coords": (0.50, 0.52)},
                "左胸 (Left Chest)": {"coords": (0.62, 0.40)},   # 穿者左=畫面右
                "右胸 (Right Chest)": {"coords": (0.38, 0.40)},  # 穿者右=畫面左
                "左臂 (Left Sleeve)": {"coords": (0.18, 0.36)},
                "右臂 (Right Sleeve)": {"coords": (0.82, 0.36)},
            },

            "pos_back": {
                # ✅ 你需求：背面只要正中間
                "背中置中 (Center)": {"coords": (0.50, 0.52)},

                # ✅ 你需求：背面延續前面袖口（main.py 的 SLEEVE_MAPPING 會用到）
                "左臂-後 (L.Sleeve Back)": {"coords": (0.18, 0.36)},
                "右臂-後 (R.Sleeve Back)": {"coords": (0.82, 0.36)},
            },
        },
    }
}
