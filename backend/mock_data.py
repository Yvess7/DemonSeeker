import json
import os
from typing import List, Dict, Any

# Top 50 Geometry Dash Demons from AREDL (All-Rated Extreme Demon List)
MOCK_TOP_DEMONS: List[Dict[str, Any]] = [
  {"position": 1, "name": "Society", "creator": "Neomarbilan"},
  {"position": 2, "name": "Thinking Space II", "creator": "CairoX"},
  {"position": 3, "name": "Amethyst", "creator": "iMist"},
  {"position": 4, "name": "Flamewall", "creator": "Narwall"},
  {"position": 5, "name": "Tidal Wave", "creator": "OniLinkGD"},
  {"position": 6, "name": "Green Bullet", "creator": "CherryTeam"},
  {"position": 7, "name": "ORBIT", "creator": "MindCap"},
  {"position": 8, "name": "Antarctic Lights", "creator": "declanlc"},
  {"position": 9, "name": "Nullscapes", "creator": "ItzKiba"},
  {"position": 10, "name": "Quanteuse processing", "creator": "Renn241"},
  {"position": 11, "name": "BOOBAWAMBA", "creator": "akunakun"},
  {"position": 12, "name": "The Bloop", "creator": "murkkat"},
  {"position": 13, "name": "Deception Dive II", "creator": "Surv"},
  {"position": 14, "name": "The Lightning Rod", "creator": "FrenchToastGD"},
  {"position": 15, "name": "Silent Clubstep", "creator": "TheRealSailent"},
  {"position": 16, "name": "Acheron", "creator": "rymari9"},
  {"position": 17, "name": "Tunnel of Despair", "creator": "Exen"},
  {"position": 18, "name": "Grief", "creator": "icedcave"},
  {"position": 19, "name": "Subterranean", "creator": "zSwip"},
  {"position": 20, "name": "Kyouki", "creator": "DemishCyan"},
  {"position": 21, "name": "Solar Flare", "creator": "Linear"},
  {"position": 22, "name": "Every End", "creator": "MindCap"},
  {"position": 23, "name": "MINUSDRY", "creator": "CDMusic"},
  {"position": 24, "name": "Kocmoc Unleashed", "creator": "CherryTeam"},
  {"position": 25, "name": "Abyss of Darkness", "creator": "Exen"},
  {"position": 26, "name": "Slaughterhouse", "creator": "icedcave"},
  {"position": 27, "name": "KOCMOC", "creator": "CherryTeam"},
  {"position": 28, "name": "SkeLeToN", "creator": "Viper88"},
  {"position": 29, "name": "Avernus", "creator": "Pman35"},
  {"position": 30, "name": "HEAVY SMOKER", "creator": "Neko9880"},
  {"position": 31, "name": "Annihilation Nation", "creator": "TheAlmightyEgg"},
  {"position": 32, "name": "Shinigami", "creator": "Peyrozz"},
  {"position": 33, "name": "Tartarus", "creator": "Riot"},
  {"position": 34, "name": "Edge of Destiny", "creator": "CDMusic"},
  {"position": 35, "name": "Firework", "creator": "Trick"},
  {"position": 36, "name": "Sakupen Circles", "creator": "Diamond"},
  {"position": 37, "name": "Verdant Landscape", "creator": "Nekrovesky"},
  {"position": 38, "name": "POOCUBED", "creator": "Liisp"},
  {"position": 39, "name": "Zodiac", "creator": "Bianox"},
  {"position": 40, "name": "Hard Machine", "creator": "Kommisar"},
  {"position": 41, "name": "The Golden", "creator": "BoBoBoBoBoBoBo"},
  {"position": 42, "name": "Sinister Silence", "creator": "Komp"},
  {"position": 43, "name": "The Hallucination", "creator": "VoTcHi"},
  {"position": 44, "name": "Arcturus", "creator": "ultracauaHD"},
  {"position": 45, "name": "Mayhem", "creator": "lCaeluml"},
  {"position": 46, "name": "Aerial Gleam", "creator": "Endlevel"},
  {"position": 47, "name": "Trueffet", "creator": "SyQual"},
  {"position": 48, "name": "Disrepute", "creator": "Zeronium"},
  {"position": 49, "name": "Bloodlust", "creator": "Knobbelboy"},
  {"position": 50, "name": "Kenophobia", "creator": "Renn241"}
]

def get_initial_demons() -> List[Dict[str, Any]]:
    """Loads the Top 50 Geometry Dash demons."""
    json_path = os.path.join(os.path.dirname(__file__), "top50_aredl.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [dict(d) for d in MOCK_TOP_DEMONS]
