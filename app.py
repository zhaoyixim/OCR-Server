from flask import Flask, request, jsonify
from flask_cors import CORS
import ddddocr
import base64
import time
import os
from PIL import Image, ImageEnhance, ImageFilter
import io

app = Flask(__name__)
CORS(app)

ocr = ddddocr.DdddOcr(det=False)

def preprocess_image(img: Image.Image):
    """预处理验证码，提高 ddddocr 识别成功率"""

    # ---------- 1. 若是 RGBA，则先将透明背景填充为白色 ----------
    if img.mode == "RGBA":
        new_img = Image.new("RGBA", img.size, (255, 255, 255, 255))
        new_img.paste(img, mask=img.split()[3])  # 以 alpha 通道作为掩码粘贴
        img = new_img.convert("RGB")  # 转为 RGB
    else:
        img = img.convert("RGB")

    # ---------- 2. 转为灰度 ----------
    img = img.convert("L")

    # ---------- 3. 自动提升亮度 ----------
    img = ImageEnhance.Brightness(img).enhance(2.0)

    # ---------- 4. 提升对比度 ----------
    img = ImageEnhance.Contrast(img).enhance(3.0)

    # ---------- 5. 降噪 ----------
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # ---------- 6. 二值化 ----------
    threshold = 160
    img = img.point(lambda x: 255 if x > threshold else 0, '1')

    return img



@app.route('/solve', methods=['POST'])
def solve_captcha():
    start_time = time.time()

    try:
        data = request.json
        image_base64 = data.get('image', '')
        checkcode = data.get('hashcode', '')
        if not checkcode or checkcode != "melonfromlocalmacandwin":
            return "ocr error"

        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        img_bytes = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(img_bytes))

        # --- ⭐ 图像预处理 ⭐ ---
        processed_img = preprocess_image(img)

        # 处理后的图像重新转为字节
        buf = io.BytesIO()
        processed_img.save(buf, format="PNG")
        processed_bytes = buf.getvalue()

        # --- ddddocr 识别 ---
        res = ocr.classification(processed_bytes)

        print(f"Recognized: {res}")
        return jsonify({"code": res, "status": "success"})

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=50205, debug=False)
