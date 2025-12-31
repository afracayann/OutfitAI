from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import google.generativeai as genai
import json
import base64
from io import BytesIO

load_dotenv()

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Google Gemini API key kontrolü
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def extract_dominant_colors(image_path: str, n_colors: int = 5):
    """Fotoğraftan baskın renkleri çıkarır"""
    img = Image.open(image_path)
    img = img.convert('RGB')
    img = img.resize((300, 300))  # Hız için resize
    
    # Piksel verilerini al
    pixels = np.array(img).reshape(-1, 3)
    
    # K-means ile renk kümeleri bul
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    
    # Baskın renkler
    colors = kmeans.cluster_centers_.astype(int)
    
    # RGB formatına çevir
    dominant_colors = [{"r": int(c[0]), "g": int(c[1]), "b": int(c[2])} for c in colors]
    
    return dominant_colors


def rgb_to_hex(r, g, b):
    """RGB'yi hex formatına çevirir"""
    return f"#{r:02x}{g:02x}{b:02x}"


def fix_json(json_string: str) -> str:
    """JSON string'ini düzeltmeye çalışır - eksik string'leri ve değerleri tamamlar"""
    import re
    
    try:
        # İlk { karakterinden başla (JSON başlangıcını bul)
        first_brace = json_string.find('{')
        if first_brace > 0:
            json_string = json_string[first_brace:]
        
        # Eksik hex değerlerini düzelt - daha güvenli pattern
        try:
            json_string = re.sub(r'"hex"\s*:\s*"([^"]*?)"', lambda m: f'"hex": "{m.group(1)}"' if m.group(1) and len(m.group(1)) >= 3 else '"hex": "#000000"', json_string)
        except Exception:
            pass
        
        # "hex": değer eksikse (sadece "hex": yazılmışsa)
        try:
            json_string = re.sub(r'"hex"\s*:\s*(?=[,}\]\n])', '"hex": "#000000"', json_string)
        except Exception:
            pass
        
        # Eksik string değerlerini düzelt - daha güvenli pattern
        try:
            # Sadece tırnak eksik olan durumları düzelt
            json_string = re.sub(r'("description"|"name"|"style"|"item"|"color"|"color_name"|"current_color"|"current_color_name"|"occasion"|"type"|"fix"|"problem"|"solution"|"reason"|"overall_assessment"|"color_harmony"|"color_temperature"|"color_contrast"|"harmony_score"|"percentage")\s*:\s*([^",}\]]+?)(?=\s*[,}\]])', r'\1: "\2"', json_string, flags=re.MULTILINE)
        except Exception as e:
            # Pattern hatası olursa atla
            pass
        
        # Eksik kapanış parantezlerini ekle
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        if open_braces > close_braces:
            json_string += '}' * (open_braces - close_braces)
        
        open_brackets = json_string.count('[')
        close_brackets = json_string.count(']')
        if open_brackets > close_brackets:
            json_string += ']' * (open_brackets - close_brackets)
        
        # Son } karakterine kadar al (JSON bitişini bul)
        last_brace = json_string.rfind('}')
        if last_brace > 0:
            json_string = json_string[:last_brace+1]
        
        # Eksik virgülleri ekle (basit durumlar için)
        try:
            json_string = re.sub(r'}\s*"', r'}, "', json_string)
            json_string = re.sub(r']\s*"', r'], "', json_string)
        except Exception:
            pass
        
        return json_string
    except Exception as e:
        # Hata olursa orijinal string'i döndür
        return json_string


def analyze_outfit_with_ai(image_path: str):
    """Analyze outfit by sending photo directly to AI"""
    if not GEMINI_API_KEY:
        return {
            "error": "API key not found",
            "is_single_item": False,
            "single_item_type": None,
            "current_outfit": {
                "description": "API key not found",
                "items": [],
                "colors": [],
                "style": "Not specified"
            },
            "compatible_items": [],
            "color_analysis": {},
            "item_color_suggestions": []
        }
    
    try:
        # Gemini görsel destekleyen model kullan
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Fotoğrafı PIL Image olarak yükle
        img = Image.open(image_path)
        
        prompt = """Analyze the outfit in this photo. Do the following:

IMPORTANT: First determine how many clothing items are in the photo:
- IF THERE IS ONLY A SINGLE CLOTHING ITEM (e.g., only a bag, only shoes, only a shirt, etc.):
  * Set is_single_item: true
  * Describe the color and features of this item
  * Suggest colors for OTHER clothing items that would match this item (compatible_items)
  * Example: If there's only a bag → Suggest pants, shirt, shoes, jacket colors that match this bag
  * Provide 3-5 different color options for each suggested item (with hex codes)
  * DO NOT create item_color_suggestions field (this field should not exist for single items)

- IF IT'S AN OUTFIT (multiple clothing items):
  * Set is_single_item: false
  1. ANALYZE THE CURRENT OUTFIT:
     - What clothing items are in the photo? (e.g., shirt, pants, shoes, bag, hat, etc.)
     - What is the current color of each clothing item?
     - What is the overall style?
     - What are the GOOD aspects of the outfit? (which colors are harmonious, which items are well chosen)
     - What are the MISSING or IMPROVABLE aspects of the outfit? (which colors should be changed, which items are missing)

  2. DETAILED COLOR ANALYSIS:
     - What are the dominant colors in the photo? (with hex codes)
     - What is the color harmony? (monochrome, complementary, analogous, etc.)
     - What is the color temperature? (warm/cool/mixed)
     - What is the color contrast? (high/medium/low)
     - Overall color palette assessment

  3. ALTERNATIVE COLOR SUGGESTIONS FOR EACH CLOTHING ITEM (item_color_suggestions):
     - Make alternative color suggestions for each item in the outfit
     - Example: "This pants color would be better if it were X" format
     - Explain why each suggested color would be better
     - Provide hex codes for suggested colors
     - Suggest 2-4 alternative colors for each item

RETURN ONLY IN JSON FORMAT:
{
  "is_single_item": true/false,
  "single_item_type": "Item name if single item (e.g., Bag), null otherwise",
  "current_outfit": {
    "description": "Current outfit description (or item description if single item)",
    "items": [
      {
        "name": "Clothing name (e.g., Shoes)",
        "color": "#HEX",
        "color_name": "Color name (e.g., Black)"
      },
      ...
    ],
    "style": "Style name",
    "colors": ["#HEX1", "#HEX2", ...],
    "good_aspects": ["List of good aspects (if outfit)"],
    "needs_improvement": ["List of improvable aspects (if outfit)"]
  },
  "compatible_items": [
    {
      "item_type": "Clothing item name (e.g., Pants)",
      "suggested_colors": [
        {
          "color": "#HEX",
          "color_name": "Color name",
          "reason": "Why this color is compatible (detailed explanation)"
        },
        ...
      ]
    },
    ...
  ],
  "color_analysis": {
    "dominant_colors": [
      {"name": "Color name", "hex": "#HEX", "percentage": "Percentage estimate"}
    ],
    "color_harmony": "Color harmony type (monochrome/complementary/analogous/triadic, etc.)",
    "color_temperature": "Warm/Cool/Mixed",
    "color_contrast": "High/Medium/Low",
    "overall_assessment": "Overall color palette assessment"
  },
  "item_color_suggestions": [  // ONLY add this field if OUTFIT (is_single_item: false)
    {
      "item": "Clothing item name (e.g., Shoes)",
      "current_color": "#HEX",
      "current_color_name": "Current color name",
      "suggested_colors": [
        {
          "color": "#HEX",
          "color_name": "Color name",
          "reason": "Why this color would be better (detailed explanation)"
        },
        ...
      ]
    },
    ...
  ]  // If is_single_item: true, do not create this field
}"""

        # Fotoğrafı ve prompt'u birlikte gönder
        response = model.generate_content(
            [img, prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Daha düşük temperature = daha tutarlı JSON
                max_output_tokens=8000,  # Çok daha fazla token
            )
        )
        
        content = response.text.strip()
        original_content = content  # Hata durumunda kullanmak için sakla
        
        # JSON'u temizle
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # JSON'u düzeltmeye çalış
        content = fix_json(content)
        
        # İlk parse denemesi
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            print(f"İlk JSON parse hatası: {e}")
            print(f"Kesilmiş yanıt (son 500 karakter): {content[-500:]}")
        
        # İkinci deneme - daha agresif düzeltme
        try:
            import re
            # Eksik hex değerlerini düzelt - daha güvenli yaklaşım
            try:
                # "hex": " şeklinde başlayıp bitmemiş olanları bul
                content = re.sub(r'"hex"\s*:\s*"([^"]{0,2})(?=\s*[,}\]])', r'"hex": "#000000"', content)
            except Exception:
                pass
            
            # "hex": yazılmış ama değer yoksa
            try:
                content = re.sub(r'"hex"\s*:\s*(?=[,}\]\n])', '"hex": "#000000"', content)
            except Exception:
                pass
            
            # Eksik kapanış parantezlerini tekrar kontrol et
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces > close_braces:
                content += '}' * (open_braces - close_braces)
            
            result = json.loads(content)
            print("JSON ikinci denemede düzeltildi ve parse edildi!")
            return result
        except (json.JSONDecodeError, re.error, Exception) as e2:
            print(f"İkinci JSON parse hatası: {e2}")
            print(f"AI yanıtı (ilk 1500 karakter): {original_content[:1500]}")
            print(f"AI yanıtı (son 500 karakter): {original_content[-500:]}")
        
        # Son çare - kısmi parse
        try:
            import re
            # En azından current_outfit'i parse etmeye çalış
            current_outfit = {}
            try:
                current_outfit_match = re.search(r'"current_outfit"\s*:\s*\{[^}]*\}', content, re.DOTALL)
                if current_outfit_match:
                    try:
                        current_outfit = json.loads('{' + current_outfit_match.group(0) + '}')['current_outfit']
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Fallback yapı
            return {
                "is_single_item": False,
                "single_item_type": None,
                "current_outfit": current_outfit or {
                    "description": "Analysis incomplete - JSON parse error",
                    "items": [],
                    "colors": [],
                    "style": "Not specified"
                },
                "compatible_items": [],
                "color_analysis": {
                    "dominant_colors": [],
                    "color_harmony": "Not specified",
                    "color_temperature": "Not specified",
                    "color_contrast": "Not specified",
                    "overall_assessment": "AI response could not be parsed. Please try again."
                },
                "item_color_suggestions": []
            }
        except Exception as e3:
            print(f"Kısmi parse hatası: {e3}")
            # En basit fallback
            return {
                "is_single_item": False,
                "single_item_type": None,
                "current_outfit": {
                    "description": "Analysis incomplete",
                    "items": [],
                    "colors": [],
                    "style": "Not specified"
                },
                "compatible_items": [],
                "color_analysis": {
                    "dominant_colors": [],
                    "color_harmony": "Not specified",
                    "color_temperature": "Not specified",
                    "color_contrast": "Not specified",
                    "overall_assessment": "AI response could not be parsed. Please try again."
                },
                "item_color_suggestions": []
            }
    except Exception as e:
        print(f"Gemini API hatası: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "is_single_item": False,
            "single_item_type": None,
            "current_outfit": {
                "description": "Hata oluştu",
                "items": [],
                "colors": [],
                "style": "Not specified"
            },
            "compatible_items": [],
            "color_analysis": {},
            "item_color_suggestions": []
        }


@app.route("/")
def read_root():
    """Ana sayfa"""
    return send_from_directory('static', 'index.html')


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Static dosyaları sun"""
    return send_from_directory('static', filename)


@app.route("/api/upload", methods=["POST"])
def upload_image():
    """Photo upload and AI analysis"""
    try:
        # Dosya kontrolü
        if 'file' not in request.files:
            abort(400, description="No file uploaded")
        
        file = request.files['file']
        if file.filename == '':
            abort(400, description="No file selected")
        
        # Dosyayı kaydet
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(file_path)
        
        # Baskın renkleri çıkar (görselleştirme için)
        dominant_colors = extract_dominant_colors(file_path)
        for color in dominant_colors:
            color["hex"] = rgb_to_hex(color["r"], color["g"], color["b"])
        
        # Fotoğrafı direkt AI'ya gönder ve analiz yap
        try:
            ai_analysis = analyze_outfit_with_ai(file_path)
        except Exception as ai_error:
            print(f"AI analiz hatası: {ai_error}")
            # Hata durumunda boş analiz döndür
            ai_analysis = {
                "is_single_item": False,
                "single_item_type": None,
                "current_outfit": {
                    "description": "Error occurred during AI analysis",
                    "items": [],
                    "colors": [],
                    "style": "Not specified"
                },
                "compatible_items": [],
                "color_analysis": {
                    "dominant_colors": [],
                    "color_harmony": "Not specified",
                    "color_temperature": "Not specified",
                    "color_contrast": "Not specified",
                    "overall_assessment": "AI analysis could not be completed. Please try again."
                },
                "item_color_suggestions": []
            }
        
        # Dosyayı base64'e çevir (frontend'de göstermek için)
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Response hazırla - tek parça varsa item_color_suggestions ekleme
        response_data = {
            "success": True,
            "is_single_item": ai_analysis.get("is_single_item", False),
            "single_item_type": ai_analysis.get("single_item_type"),
            "dominant_colors": dominant_colors,
            "current_outfit": ai_analysis.get("current_outfit", {}),
            "compatible_items": ai_analysis.get("compatible_items", []),
            "color_analysis": ai_analysis.get("color_analysis", {}),
            "image": f"data:image/jpeg;base64,{image_data}"
        }
        
        # Sadece kombin varsa item_color_suggestions ekle
        if not ai_analysis.get("is_single_item", False):
            response_data["item_color_suggestions"] = ai_analysis.get("item_color_suggestions", [])
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Hata mesajını daha anlaşılır hale getir
        error_message = str(e)
        if "pattern" in error_message.lower() or "regex" in error_message.lower():
            error_message = "JSON parse error: AI response not in expected format. Please try again."
        elif "JSON" in error_message or "json" in error_message:
            error_message = "JSON parse error: AI response could not be processed. Please try again."
        abort(500, description=f"Hata: {error_message}")


@app.route("/api/check-api-key", methods=["GET", "POST"])
def check_api_key():
    """Check API key"""
    return jsonify({
        "has_api_key": bool(GEMINI_API_KEY),
        "message": "Gemini API key available" if GEMINI_API_KEY else "API key not found. Add GEMINI_API_KEY to .env file."
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)