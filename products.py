# products.py - 產品資料庫

PRODUCT_CATALOG = {
    "團體服系列": {
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",
            
            # 1. 設定圖片路徑前綴 (指向 assets 資料夾，不含顏色部分)
            # 程式會自動組合成: assets/AG21000_[顏色碼]_[front/back].png
            "image_base": "assets/AG21000", 
            
            # 2. 顏色選單 (顯示給客戶看的中文名稱)
            "colors": [
                "白色 (White)", "黑色 (Black)", "麻灰 (Heather Gray)", "炭灰 (Charcoal Gray)", "鐵灰 (Slate Gray)",
                "丈青 (Navy)", "寶藍 (Royal Blue)", "霧藍 (Dusty Blue)", "蒂芬妮藍 (Tiffany Blue)",
                "森林綠 (Forest Green)", "抹茶綠 (Matcha Green)", "薄荷綠 (Mint Green)",
                "酒紅 (Burgundy)", "紅色 (Red)", "蜜桃橘 (Peach Orange)",
                "黃色 (Yellow)", "琥珀黃 (Amber Yellow)", "奶茶色 (Beige Brown)", "卡其 (Khaki)", "淺粉 (Light Pink)"
            ],
            
            # 3. 顏色代碼對照表 (Key要跟上面選單一樣，Value要跟檔名中間那段一樣)
            # 例如檔名是 AG21000_AmberYellow_front.png，Value 就是 "AmberYellow"
            "color_map": {
                "白色 (White)": "White",
                "黑色 (Black)": "Black",
                "麻灰 (Heather Gray)": "HeatherGray",
                "炭灰 (Charcoal Gray)": "CharcoalGray",
                "鐵灰 (Slate Gray)": "SlateGray",
                "丈青 (Navy)": "Navy",
                "寶藍 (Royal Blue)": "RoyalBlue",
                "霧藍 (Dusty Blue)": "DustyBlue",
                "蒂芬妮藍 (Tiffany Blue)": "TiffanyBlue",
                "森林綠 (Forest Green)": "ForestGreen",
                "抹茶綠 (Matcha Green)": "MatchaGreen",
                "薄荷綠 (Mint Green)": "MintGreen",
                "酒紅 (Burgundy)": "Burgundy",
                "紅色 (Red)": "Red",
                "蜜桃橘 (Peach Orange)": "PeachOrange",
                "黃色 (Yellow)": "Yellow",
                "琥珀黃 (Amber Yellow)": "AmberYellow",
                "奶茶色 (Beige Brown)": "BeigeBrown",
                "卡其 (Khaki)": "Khaki",
                "淺粉 (Light Pink)": "LightPink"
            },
            
            # 4. 正面印刷位置 (座標)
            "pos_front": {
                "正中間": {"coords": (300, 400)},
                "左胸": {"coords": (420, 280)},
                "右胸": {"coords": (180, 280)},
                "左臂": {"coords": (520, 320)},
                "右臂": {"coords": (80, 320)}
            },
            
            # 5. 背面印刷位置 (座標)
            "pos_back": {
                "背後正中": {"coords": (300, 350)},
                "左臂(後)": {"coords": (520, 320)},
                "右臂(後)": {"coords": (80, 320)}
            }
        }
    }
}
