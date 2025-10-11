#!/usr/bin/env python3
"""
Greenhouse Image Analyzer
Analysiert Gewächshaus-Bilder mit OpenAI GPT-4 Vision
"""

import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
import requests
from PIL import Image
from io import BytesIO


def compress_image(image_path, max_size=(1280, 1280)):
    img = Image.open(image_path)
    img.thumbnail(max_size)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_analysis_prompt():
    """Strukturierter Prompt für die Pflanzenanalyse"""
    return """Analysiere alle Pflanzen die du auf diesem Gewächshaus-Foto siehst detailliert:

1. PFLANZEN: Erkenne und bewerte jede Pflanze (Typ, Wachstumsstadium 0-100%, Position)
2. GESUNDHEIT: Allgemeiner Zustand, erkannte Probleme, konkrete Empfehlungen
3. UMGEBUNG: Bewässerung, Licht, Temperatur-Anzeichen

Antwort als JSON:
{
  "timestamp": "2024-01-01 12:00:00",
  "plants": [
    {
      "type": "Tomate", 
      "growth": 75, 
      "position": "links vorne",
      "health": "gut/mäßig/schlecht",
      "notes": "Beschreibung"
    }
  ],
  "overall_health": {
    "status": "gut/mäßig/schlecht",
    "score": 85,
    "issues": ["Problem 1", "Problem 2"],
    "recommendations": ["Empfehlung 1", "Empfehlung 2"]
  },
  "environment": {
    "watering": "ausreichend/zu wenig/zu viel",
    "light": "gut/schlecht",
    "notes": "Umgebungsnotizen"
  }
}"""

def encode_image_base64(image_path):
    """Bild als Base64 kodieren"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            print(f"Bild kodiert: {len(encoded)} Zeichen")
            return encoded
    except Exception as e:
        print(f"Fehler beim Kodieren des Bildes: {e}")
        return None

def analyze_with_openai(image_base64):
    """Bildanalyse mit OpenAI GPT-4 Vision via REST API"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OPENAI_API_KEY nicht gefunden")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": get_analysis_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        
        print("Sende Request an OpenAI API...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API Fehler {response.status_code}: {response.text}")
        
        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise Exception(f"Keine Antwort in API Response: {result}")
        
        content = result["choices"][0]["message"]["content"]
        tokens_used = result.get("usage", {}).get("total_tokens", 0)
        
        print(f"OpenAI Response erhalten: {tokens_used} Tokens verwendet")
        return content, tokens_used
        
    except requests.exceptions.Timeout:
        print("API Request Timeout")
        return None, 0
    except requests.exceptions.RequestException as e:
        print(f"API Request Fehler: {e}")
        return None, 0
    except Exception as e:
        print(f"OpenAI API Fehler: {e}")
        return None, 0

def timestamp_from_filename(filename):
    """Extrahiert den Timestamp aus dem Dateinamen greenhouse_YYYYMMDDHHMMSS.jpg"""
    try:
        stem = Path(filename).stem  # z.B. 'greenhouse_20250924143055'
        timestamp_str = stem.split('_')[1]  # '20250924143055'
        return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # Fallback auf aktuelle Zeit
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_analysis_result(content, image_filename):
    """JSON-Antwort parsen und Timestamp sicherstellen"""
    try:
        # Markdown Codeblock entfernen, falls vorhanden
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        
        result = json.loads(content)
        
        # Timestamp aus Filename oder aktuelle Zeit
        result["timestamp"] = timestamp_from_filename(image_filename)
            
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Fehler: {e}")
        return {
            "timestamp": timestamp_from_filename(image_filename),
            "raw_analysis": content,
            "parse_error": str(e),
            "status": "parse_failed"
        }

def save_analysis_results(image_filename, analysis_data, tokens_used):
    """Analyseergebnisse in JSON-Datei speichern"""
    try:
        analysis_dir = Path("analysis")
        analysis_dir.mkdir(exist_ok=True)
        
        image_name = Path(image_filename).stem
        analysis_file = analysis_dir / f"{image_name}_analysis.json"
        
        analysis_data["meta"] = {
            "source_image": image_filename,
            "analysis_time": datetime.now().isoformat(),
            "tokens_used": tokens_used,
            "model": "gpt-4o"
        }
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
        print(f"Analyse gespeichert: {analysis_file}")
        return analysis_file
        
    except Exception as e:
        print(f"Fehler beim Speichern: {e}")
        return None

def generate_summary_report():
    """Zusammenfassungsbericht aller Analysen erstellen"""
    try:
        analysis_dir = Path("analysis")
        if not analysis_dir.exists():
            return
            
        analyses = []
        for analysis_file in analysis_dir.glob("*_analysis.json"):
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    analyses.append(data)
            except Exception as e:
                print(f"Fehler beim Laden von {analysis_file}: {e}")
        
        if not analyses:
            return
            
        analyses.sort(key=lambda x: x.get("timestamp", ""))
        
        report = "# Gewächshaus Analyse Report\n\n"
        report += f"Letzte Aktualisierung: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if analyses:
            latest = analyses[-1]
            report += "## 📊 Aktuelle Situation\n\n"
            
            if "overall_health" in latest:
                health = latest["overall_health"]
                status_emoji = {"gut": "✅", "mäßig": "⚠️", "schlecht": "❌"}.get(health.get("status"), "❓")
                report += f"**Gesamtzustand:** {status_emoji} {health.get('status', 'unbekannt')}\n\n"
                if health.get("score"):
                    report += f"**Score:** {health['score']}/100\n\n"
            
            if "plants" in latest and latest["plants"]:
                report += "### 🌱 Erkannte Pflanzen\n\n"
                for plant in latest["plants"]:
                    report += f"- **{plant.get('type', 'Unbekannt')}** "
                    report += f"({plant.get('growth', 0)}% Wachstum) - "
                    report += f"{plant.get('position', 'Position unbekannt')}\n"
                report += "\n"
        
        report += "## 📈 Verlauf (letzte 10 Analysen)\n\n"
        report += "| Datum | Zeit | Status | Pflanzen | Probleme |\n"
        report += "|-------|------|--------|----------|----------|\n"
        
        for analysis in analyses[-10:]:
            timestamp = analysis.get("timestamp", "")
            date, time = (timestamp.split(" ", 1) + [""])[:2]
            status = "❓"
            if "overall_health" in analysis:
                health_status = analysis["overall_health"].get("status", "")
                status = {"gut": "✅", "mäßig": "⚠️", "schlecht": "❌"}.get(health_status, "❓")
            plant_count = len(analysis.get("plants", []))
            issue_count = len(analysis.get("overall_health", {}).get("issues", []))
            report += f"| {date} | {time} | {status} | {plant_count} | {issue_count} |\n"
        
        with open("README.md", 'w', encoding='utf-8') as f:
            f.write(report)
            
        print("📊 Summary Report aktualisiert: README.md")
        
    except Exception as e:
        print(f"Fehler beim Erstellen des Reports: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_greenhouse.py <image_path>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Bild nicht gefunden: {image_path}")
        sys.exit(1)
        
    if not os.getenv('OPENAI_API_KEY'):
        print("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    print(f"🔍 Analysiere Bild: {image_path}")
    
    image_base64 = compress_image(image_path)
    if not image_base64:
        sys.exit(1)
    
    analysis_content, tokens = analyze_with_openai(image_base64)
    if not analysis_content:
        sys.exit(1)
    
    analysis_data = parse_analysis_result(analysis_content, image_path)
    
    analysis_file = save_analysis_results(image_path, analysis_data, tokens)
    if not analysis_file:
        sys.exit(1)
    
    generate_summary_report()
    
    print("✅ Analyse abgeschlossen!")
    if "overall_health" in analysis_data:
        health = analysis_data["overall_health"]
        print(f"Gesamtzustand: {health.get('status', 'unbekannt')}")
        if health.get("issues"):
            print(f"Probleme: {', '.join(health['issues'])}")

if __name__ == "__main__":
    main()
