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
                "米褐 (BeigeBrown)"
            ],
            
            # 2. 顏色對應表 (顯示名稱 -> 檔名關鍵字)
            # 這裡的英文必須跟您 assets 資料夾裡的檔名一模一樣 (區分大小寫)
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
                "米褐 (BeigeBrown)": "BeigeBrown"
            },
            
            # 3. 檔名開頭 (圖片必須放在 assets 資料夾內)
            "image_base": "AG21000",
            
            # 4. 正面印刷位置
            "pos_front": {
                "正中間 (Center)": {"coords": (380, 270)},
                "左胸 (Left Chest)": {"coords": (450, 230)},  
                "右胸 (Right Chest)": {"coords": (300, 230)}, 
                "左臂 (Left Sleeve)": {"coords": (720, 150), "default_rot": 55}, 
                "右臂 (Right Sleeve)": {"coords": (50, 180), "default_rot": -45}   
            },
            
            # 5. 背面印刷位置
            "pos_back": {
                "背後正中 (Center)": {"coords": (500, 320)},
                "左臂-後 (L.Sleeve Back)": {"coords": (950, 240)},
                "右臂-後 (R.Sleeve Back)": {"coords": (80, 270)}
            }
        }
    }
    "CP101 吸濕排汗團體服": {
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
        "太妃糖色": "toffee"
    },

    "pos_front": {
        "胸口置中": {"coords": (300, 360)},
        "左胸小字": {"coords": (220, 340)},
        "右胸小字": {"coords": (380, 340)}
    },

    "pos_back": {
        "背中置中": {"coords": (300, 360)},
        "上背字樣": {"coords": (300, 280)}
    }
}

}



































