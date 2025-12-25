# products.py - 產品資料庫 (支援 assets 資料夾)

PRODUCT_CATALOG = {
    "團體服系列": {
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",
            # 1. 設定圖片路徑前綴 (指向 assets 資料夾)
            "image_base": "assets/AG21000", 
            
            # 2. 顏色設定
            "colors": ["白 (White)", "黑 (Black)", "丈青 (Navy)"],
            "color_map": {
                "白 (White)": "White",
                "黑 (Black)": "Black",
                "丈青 (Navy)": "Navy"
            },
            
            # 3. 正面印刷位置 (座標)
            "pos_front": {
                "正中間": {"coords": (300, 400)},
                "左胸": {"coords": (420, 280)},
                "右胸": {"coords": (180, 280)},
                "左臂": {"coords": (520, 320)},
                "右臂": {"coords": (80, 320)}
            },
            
            # 4. 背面印刷位置 (座標)
            "pos_back": {
                "背後正中": {"coords": (300, 350)},
                "左臂(後)": {"coords": (520, 320)},
                "右臂(後)": {"coords": (80, 320)}
            }
        }
    }
}
