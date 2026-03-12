"""
Greenhouse Image Analyzer
Analysiert Gewächshaus-Bilder mit OpenAI GPT-4 Vision
und gibt Wachstums- und Gesundheitszustand als Json zurück.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import requests


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


def analysiere_mit_openai(bild_url):
    """Bildanalyse mit OpenAI GPT-4 Vision via öffentlicher Bild-URL"""
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
                                "url": bild_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
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
        stamm = Path(dateiname).stem
        zeitstempel_text = stamm.split('_')[1]
        return datetime.strptime(zeitstempel_text, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_analyse_ergebnis(inhalt, bild_url):
    """JSON-Antwort parsen und Timestamp sicherstellen"""
    try:
        if "```json" in inhalt:
            json_start = inhalt.find("```json") + 7
            json_ende = inhalt.find("```", json_start)
            inhalt = inhalt[json_start:json_ende].strip()
        elif "```" in inhalt:
            json_start = inhalt.find("```") + 3
            json_ende = inhalt.find("```", json_start)
            inhalt = inhalt[json_start:json_ende].strip()

        ergebnis = json.loads(inhalt)
        ergebnis["timestamp"] = zeitstempel_aus_dateiname(bild_url)
        return ergebnis

    except json.JSONDecodeError as fehler:
        print(f"JSON Parse Fehler: {fehler}")
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "raw_analysis": inhalt,
            "parse_error": str(fehler),
            "status": "parse_failed"
        }


def speichere_analyse_ergebnisse(bild_url, analyse_daten, tokens_verbraucht):
    """Analyseergebnisse in JSON-Datei speichern"""
    try:
        analyse_ordner = Path("analysis")
        analyse_ordner.mkdir(exist_ok=True)

        # Dateiname aus URL ableiten
        bildname = Path(bild_url.split("/")[-1]).stem
        analyse_datei = analyse_ordner / f"{bildname}_analysis.json"

        analyse_daten["meta"] = {
            "source_image": bild_url,
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
        print("Usage: python analyze_greenhouse.py <image_url>")
        sys.exit(1)

    bild_url = sys.argv[1]

    if not bild_url.startswith("http://") and not bild_url.startswith("https://"):
        print("Fehler: Es muss eine öffentliche HTTP/HTTPS-URL angegeben werden")
        sys.exit(1)

    if not os.getenv('OPENAI_API_KEY'):
        print("OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    print(f"Analysiere Bild: {bild_url}")

    analyse_inhalt, tokens = analysiere_mit_openai(bild_url)
    if not analyse_inhalt:
        sys.exit(1)

    analyse_daten = parse_analyse_ergebnis(analyse_inhalt, bild_url)

    analyse_datei = speichere_analyse_ergebnisse(bild_url, analyse_daten, tokens)
    if not analyse_datei:
        sys.exit(1)

    print("Analyse abgeschlossen!")


if __name__ == "__main__":
    main()
