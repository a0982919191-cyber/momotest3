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
                "左臂 (Left Sleeve)": {"coords": (720, 150), "default_rot": 48}, 
                "右臂 (Right Sleeve)": {"coords": (80, 180), "default_rot": -45}   
            },
            
            # 5. 背面印刷位置
            "pos_back": {
                "背後正中 (Center)": {"coords": (500, 320)},
                "左臂-後 (L.Sleeve Back)": {"coords": (520, 320)},
                "右臂-後 (R.Sleeve Back)": {"coords": (80, 320)}
            }
        }
    }
}






















