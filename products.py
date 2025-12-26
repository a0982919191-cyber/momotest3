PRODUCT_CATALOG = {
    "團體服系列": {
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",
            # 1. 顏色選項 (顯示名稱)
            "colors": ["白 (White)", "黑 (Black)", "丈青 (Navy)"],
            
            # 2. 顏色對應表 (顯示名稱 -> 檔名關鍵字)
            # 您的圖片檔名必須包含這些英文關鍵字
            "color_map": {
                "白 (White)": "White",
                "黑 (Black)": "Black",
                "丈青 (Navy)": "Navy"
            },
            
            # 3. 檔名開頭 (Image Base Name)
            "image_base": "AG21000",
            
            # 4. 正面印刷位置與座標 (X, Y)
            # 座標是以 600x800 的畫布為基準
            "pos_front": {
                "正中間 (Center)": {"coords": (300, 400)},
                "左胸 (Left Chest)": {"coords": (420, 280)},  # 穿著者的左邊
                "右胸 (Right Chest)": {"coords": (180, 280)}, # 穿著者的右邊
                "左臂 (Left Sleeve)": {"coords": (520, 320)}, # 畫面右側
                "右臂 (Right Sleeve)": {"coords": (80, 320)}   # 畫面左側
            },
            
            # 5. 背面印刷位置與座標
            "pos_back": {
                "背後正中 (Center)": {"coords": (300, 350)},
                "左臂-後 (L.Sleeve Back)": {"coords": (520, 320)},
                "右臂-後 (R.Sleeve Back)": {"coords": (80, 320)}
            }
        }
    }
}
