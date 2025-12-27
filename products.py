# products.py
# 這是產品資料庫，新增產品改這裡就好

PRODUCT_CATALOG = {
    "團體服系列": {
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",

            # 1. 顏色選項 (顯示在選單上的名稱)
            "colors": [
                "白 (White)",
                "黑 (Black)",
                "丈青 (Navy)",
                "麻灰 (HeatherGray)",
                "炭灰 (CharcoalGray)",
                "石板灰 (SlateGray)",
                "紅 (Red)",
                "酒紅 (Burgundy)",
                "寶藍 (RoyalBlue)",
                "霧霾藍 (DustyBlue)",
                "蒂芬妮藍 (TiffanyBlue)",
                "森林綠 (ForestGreen)",
                "抹茶綠 (MatchaGreen)",
                "薄荷綠 (MintGreen)",
                "黃 (Yellow)",
                "琥珀黃 (AmberYellow)",
                "蜜桃橘 (PeachOrange)",
                "淺粉 (LightPink)",
                "卡其 (Khaki)",
                "米褐 (BeigeBrown)",
            ],

            # 2. 顏色對應表 (顯示名稱 -> 檔名關鍵字)
            "color_map": {
                "白 (White)": "White",
                "黑 (Black)": "Black",
                "丈青 (Navy)": "Navy",
                "麻灰 (HeatherGray)": "HeatherGray",
                "炭灰 (CharcoalGray)": "CharcoalGray",
                "石板灰 (SlateGray)": "SlateGray",
                "紅 (Red)": "Red",
                "酒紅 (Burgundy)": "Burgundy",
                "寶藍 (RoyalBlue)": "RoyalBlue",
                "霧霾藍 (DustyBlue)": "DustyBlue",
                "蒂芬妮藍 (TiffanyBlue)": "TiffanyBlue",
                "森林綠 (ForestGreen)": "ForestGreen",
                "抹茶綠 (MatchaGreen)": "MatchaGreen",
                "薄荷綠 (MintGreen)": "MintGreen",
                "黃 (Yellow)": "Yellow",
                "琥珀黃 (AmberYellow)": "AmberYellow",
                "蜜桃橘 (PeachOrange)": "PeachOrange",
                "淺粉 (LightPink)": "LightPink",
                "卡其 (Khaki)": "Khaki",
                "米褐 (BeigeBrown)": "BeigeBrown",
            },

            # 3. 檔名開頭 (圖片必須放在 assets 資料夾內)
            "image_base": "AG21000",

            # 4. 正面印刷位置
            "pos_front": {
                "正中間 (Center)": {"coords": (380, 270)},
                "左胸 (Left Chest)": {"coords": (450, 230)},
                "右胸 (Right Chest)": {"coords": (300, 230)},
                "左臂 (Left Sleeve)": {"coords": (720, 150), "default_rot": 55},
                "右臂 (Right Sleeve)": {"coords": (50, 180), "default_rot": -45},
            },

            # 5. 背面印刷位置
            "pos_back": {
                "背後正中 (Center)": {"coords": (500, 320)},
                "左臂-後 (L.Sleeve Back)": {"coords": (950, 240)},
                "右臂-後 (R.Sleeve Back)": {"coords": (80, 270)},
            },
        },

        "CP101 吸濕排汗團體服": {
            "name": "CP101 吸濕排汗團體服",
            "image_base": "CP101",

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

            # 檔名對應：建議 assets 檔名格式
            # CP101_<code>_front.png / CP101_<code>_back.png
            "color_map": {
                "白色": "White",
                "淺灰色": "LightGray",
                "深灰色": "DarkGray",
                "黑色": "Black",
                "粉紅色": "Pink",
                "玫紅色": "Rose",
                "紅色": "Red",
                "酒紅色": "Wine",
                "水藍色": "SkyBlue",
                "湖藍色": "LakeBlue",
                "寶藍色": "RoyalBlue",
                "藏青色": "Navy",
                "海藍色": "SeaBlue",
                "草綠色": "GrassGreen",
                "墨綠色": "DarkGreen",
                "卡其色": "Khaki",
                "淺黃色": "LightYellow",
                "黃色": "Yellow",
                "淺紫色": "LightPurple",
                "深紫色": "DarkPurple",
                "螢光粉色": "NeonPink",
                "螢光橘色": "NeonOrange",
                "螢光綠色": "NeonGreen",
                "螢光黃色": "NeonYellow",
                "奶茶色": "MilkTea",
                "蓮藕粉色": "LotusPink",
                "玫瑰粉色": "RosePink",
                "瑪瑙紅色": "AgateRed",
                "芥末黃色": "Mustard",
                "金色": "Gold",
                "南瓜橘色": "Pumpkin",
                "珊瑚橘色": "Coral",
                "天空藍色": "Sky",
                "薰衣草色": "LavenderBlue",
                "星空灰色": "SpaceGray",
                "鯨魚藍色": "WhaleBlue",
                "翡翠綠色": "Emerald",
                "軍綠色": "Army",
                "駝色": "Camel",
                "太妃糖色": "Toffee",
            },

            "pos_front": {
                "正中間 (Center)": {"coords": (300, 360)},
                "左胸 (Left Chest)": {"coords": (220, 340)},
                "右胸 (Right Chest)": {"coords": (380, 340)},
            },

            "pos_back": {
                "背中置中 (Center)": {"coords": (300, 360)},
                "上背字樣 (Upper Back)": {"coords": (300, 280)},
            },
        },
    }
}
