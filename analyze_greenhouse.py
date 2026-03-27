"""
Greenhouse Image Analyzer
Analysiert Gewächshaus-Bilder mit OpenAI GPT-4 Vision
und gibt Wachstums- und Gesundheitszustand als Json zurück.
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


def bild_komprimieren(bildpfad, max_groesse=(1280, 1280)):
    bild = Image.open(bildpfad)
    bild.thumbnail(max_groesse)
    puffer = BytesIO()
    bild.save(puffer, format="JPEG", quality=70)
    return base64.b64encode(puffer.getvalue()).decode("utf-8")


def hole_analyse_prompt():
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

def kodiere_bild_base64(bildpfad):
    """Bild als Base64 kodieren"""
    try:
        with open(bildpfad, 'rb') as bilddatei:
            kodiert = base64.b64encode(bilddatei.read()).decode('utf-8')
            print(f"Bild kodiert: {len(kodiert)} Zeichen")
            return kodiert
    except Exception as fehler:
        print(f"Fehler beim Kodieren des Bildes: {fehler}")
        return None

def analysiere_mit_openai(bild_base64):
    """Bildanalyse mit OpenAI GPT-4 Vision mit REST API"""
    try:
        api_schluessel = os.getenv('OPENAI_API_KEY')
        if not api_schluessel:
            raise Exception("OPENAI_API_KEY nicht gefunden")
        
        kopfzeilen = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_schluessel}"
        }
        
        nutzlast = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": hole_analyse_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{bild_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000
        }

        
        print("Sende Request an OpenAI API...")
        antwort = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=kopfzeilen,
            json=nutzlast,
            timeout=60
        )
        
        if antwort.status_code != 200:
            raise Exception(f"API Fehler {antwort.status_code}: {antwort.text}")
        
        ergebnis = antwort.json()
        if "choices" not in ergebnis or not ergebnis["choices"]:
            raise Exception(f"Keine Antwort in API Response: {ergebnis}")
        
        inhalt = ergebnis["choices"][0]["message"]["content"]
        print(f"=== API ANTWORT ===")
        print(repr(inhalt))  # repr() zeigt auch None, \n, etc.
        print(f"==================")
        tokens_verbraucht = ergebnis.get("usage", {}).get("total_tokens", 0)
        
        print(f"OpenAI Response erhalten: {tokens_verbraucht} Tokens verwendet")
        return inhalt, tokens_verbraucht
        
    except requests.exceptions.Timeout:
        print("API Request Timeout")
        return None, 0
    except requests.exceptions.RequestException as fehler:
        print(f"API Request Fehler: {fehler}")
        return None, 0
    except Exception as fehler:
        print(f"OpenAI API Fehler: {fehler}")
        return None, 0

def zeitstempel_aus_dateiname(dateiname):
    """Extrahiert den Timestamp aus dem Dateinamen greenhouse_YYYYMMDDHHMMSS.jpg"""
    try:
        stamm = Path(dateiname).stem  # z.B. 'greenhouse_20250924143055'
        zeitstempel_text = stamm.split('_')[1]  # '20250924143055'
        return datetime.strptime(zeitstempel_text, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # Fallback auf aktuelle Zeit
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_analyse_ergebnis(inhalt, bild_dateiname):
    """JSON-Antwort parsen und Timestamp sicherstellen"""
    try:
        # Markdown Codeblock entfernen, falls vorhanden
        if "```json" in inhalt:
            json_start = inhalt.find("```json") + 7
            json_ende = inhalt.find("```", json_start)
            inhalt = inhalt[json_start:json_ende].strip()
        elif "```" in inhalt:
            json_start = inhalt.find("```") + 3
            json_ende = inhalt.find("```", json_start)
            inhalt = inhalt[json_start:json_ende].strip()
        
        ergebnis = json.loads(inhalt)
        
        # Timestamp aus Filename oder aktuelle Zeit
        ergebnis["timestamp"] = zeitstempel_aus_dateiname(bild_dateiname)
            
        return ergebnis
        
    except json.JSONDecodeError as fehler:
        print(f"JSON Parse Fehler: {fehler}")
        return {
            "timestamp": zeitstempel_aus_dateiname(bild_dateiname),
            "raw_analysis": inhalt,
            "parse_error": str(fehler),
            "status": "parse_failed"
        }

def speichere_analyse_ergebnisse(bild_dateiname, analyse_daten, tokens_verbraucht):
    """Analyseergebnisse in JSON-Datei speichern"""
    try:
        analyse_ordner = Path("analysis")
        analyse_ordner.mkdir(exist_ok=True)
        
        bildname = Path(bild_dateiname).stem
        analyse_datei = analyse_ordner / f"{bildname}_analysis.json"
        
        analyse_daten["meta"] = {
            "source_image": bild_dateiname,
            "analysis_time": datetime.now().isoformat(),
            "tokens_used": tokens_verbraucht,
            "model": "gpt-4o-mini"
        }
        
        with open(analyse_datei, 'w', encoding='utf-8') as datei:
            json.dump(analyse_daten, datei, indent=2, ensure_ascii=False)
            
        print(f"Analyse gespeichert: {analyse_datei}")
        return analyse_datei
        
    except Exception as fehler:
        print(f"Fehler beim Speichern: {fehler}")
        return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_greenhouse.py <image_path>")
        sys.exit(1)
        
    bildpfad = sys.argv[1]
    
    if not os.path.exists(bildpfad):
        print(f"Bild nicht gefunden: {bildpfad}")
        sys.exit(1)
        
    if not os.getenv('OPENAI_API_KEY'):
        print("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    print(f"Analysiere Bild: {bildpfad}")
    
    bild_base64 = bild_komprimieren(bildpfad)
    if not bild_base64:
        sys.exit(1)
    
    analyse_inhalt, tokens = analysiere_mit_openai(bild_base64)
    if not analyse_inhalt:
        sys.exit(1)
    
    analyse_daten = parse_analyse_ergebnis(analyse_inhalt, bildpfad)
    
    analyse_datei = speichere_analyse_ergebnisse(bildpfad, analyse_daten, tokens)
    if not analyse_datei:
        sys.exit(1)
    
    print("Analyse abgeschlossen!")
    

if __name__ == "__main__":
    main()
