# -*- coding: utf-8 -*-
"""Baut das Beispiel-JSON fuer Linie 223 und schreibt beispiel_223.json."""
import json

STOPS = [
    ("RE Hbf", True, None),
    ("An der Lehmkuhle", False, None),
    ("Franz-Bracht-Str.", False, None),
    ("Beisinger Weg", False, None),
    ("Ruhrfestspielhaus", False, None),
    ("Sternwarte", False, None),
    ("Schrebergarten", False, None),
    ("Auf dem Siepen", False, None),
    ("Findling", False, None),
    ("Marl Flugplatz", True, None),
    ("Korthausen", False, None),
    ("Lenkerbeck Feuerwehrhaus", False, None),
    ("Lisztstr.", False, None),
    ("Brucknerstr.", False, None),
    ("Fanny-Hensel-Weg", False, None),
    ("Sibeliusstr.", False, None),
    ("Ringerottstr.", False, None),
    ("Zur Loemühle", False, None),
    ("Loekamptor", False, None),
    ("Otto-Wels-Str.", False, None),
    ("Paracelsus-Klinik", False, None),
    ("Gudrunstr.", False, None),
    ("Kriemhildestr.", False, None),
    ("Gendorfer Str.", False, None),
    ("Harkortschule", False, None),
    ("Feierabendhaus", False, None),
    ("Chemiepark Marl", False, None),
    ("Kampstr.", False, None),
    ("Robert-Bunsen-Str.", False, None),
    ("Schreierstr.", False, None),
    ("Herzlia-Center", False, None),
    ("Marl Mitte", True, "S"),
]
N = len(STOPS)
PARA = 20  # Index Paracelsus-Klinik (0-basiert)

stops = [{"name": n, "bold": b, "symbol": s} for (n, b, s) in STOPS]


def empty():
    return [""] * N


def short_col(start_minutes):
    """Kurzfahrt ab Paracelsus-Klinik. start_minutes: Liste fuer PARA..Marl Mitte (12 Werte)."""
    c = empty()
    for i, v in enumerate(start_minutes):
        c[PARA + i] = v
    return c


def full_col(values):
    """values: Liste der 32 Zellen."""
    assert len(values) == N, len(values)
    return list(values)


# ---- Kurzfahrten-Minuten (Para -> Marl Mitte) ----
def short(prefixhour, first):
    """first = volle Startzeit (z.B. '4.41'), Folge-Minuten fix nach Muster."""
    mins = ["42", "43", "44", "45", "47", "48", "51", "52", "53", "55"]
    last = {"4": "4.57", "5.11": "5.27", "5.41": "5.57", "6.11": "6.27"}
    return [first] + mins + [last[prefixhour]]


# ================= MONTAG–FREITAG =================
mf_short = [
    {"header": "phone", "cells": short_col(short("4", "4.41"))},
    {"header": "phone", "cells": short_col(short("5.11", "5.11"))},
    {"cells": short_col(short("5.41", "5.41"))},
    {"cells": short_col(short("6.11", "6.11"))},
]

# Hauptspalten: [an_der_lehmkuhle ...] Minutenmuster ab An der Lehmkuhle
# Muster der "Folgeminuten" relativ:
PAT = ["15", "16", "17", "18", "19", "21", "23", "24", "25",  # bis Marl Flugplatz
       "26", "27", "28", "29", "30", "31", "32", "33", "35", "36",  # bis Otto-Wels
       "38", "39", "40", "41", "42", "44", "45", "49", "50", "51", "53"]  # bis Herzlia


def mf_full(start, lastmitte, pat):
    return full_col([start] + pat + [lastmitte])


mf_6_12 = mf_full("6.12", "6.56", PAT)
# 20.12 Spalte: identisches Minutenmuster wie 6.12
mf_20_12 = mf_full("20.12", "20.56", PAT)
# 20.46 Spalte
pat_2046 = ["49", "50", "51", "52", "53", "55", "57", "58", "59",
            "21.00", "01", "02", "03", "04", "05", "06", "07", "09", "10",
            "11", "12", "13", "14", "15", "17", "18", "21", "22", "23", "25"]
mf_20_46 = mf_full("20.46", "21.27", pat_2046)
pat_2146 = ["49", "50", "51", "52", "53", "55", "57", "58", "59",
            "22.00", "01", "02", "03", "04", "05", "06", "07", "09", "10",
            "11", "12", "13", "14", "15", "17", "18", "21", "22", "23", "25"]
mf_21_46 = mf_full("21.46", "22.27", pat_2146)

mf_columns = mf_short + [
    {"cells": mf_6_12},
    {"type": "triangle", "color": "#3aaa35"},
    {"cells": mf_20_12},
    {"type": "interval", "text": "alle 30 Min."},
    {"cells": mf_20_46},
    {"cells": mf_21_46},
]

section_mf = {"title": "Montag–Freitag", "color": "#3aaa35", "columns": mf_columns}

# ================= SAMSTAG =================
# Spalten: 6.46, 7.46, 8.42, [tri], 16.42, 17.42, 18.46, [interval60], 21.46
sa_pat_x46 = ["49", "50", "51", "52", "53", "55", "57", "58", "59",
              None, "01", "02", "03", "04", "05", "06", "07", "09", "10",
              "11", "12", "13", "14", "15", "17", "18", "21", "22", "23", "25"]


def sa_col(start, korthausen, lastmitte):
    pat = list(sa_pat_x46)
    pat[9] = korthausen  # Korthausen-Wert
    return full_col([start] + pat + [lastmitte])


sa_646 = sa_col("6.46", "7.00", "7.27")
sa_746 = sa_col("7.46", "8.00", "8.27")
# 8.42: kreuzt die Stunde -> Fanny-Hensel-Weg 9.00
sa_842_pat = ["45", "46", "47", "48", "49", "51", "53", "54", "55",
              "56", "57", "58", "59", "9.00", "01", "02", "03", "05", "06",
              "08", "09", "10", "11", "12", "14", "15", "19", "20", "21", "23"]
sa_842 = full_col(["8.42"] + sa_842_pat + ["9.26"])
sa_1642_pat = ["45", "46", "47", "48", "49", "51", "53", "54", "55",
               "56", "57", "58", "59", "17.00", "01", "02", "03", "05", "06",
               "08", "09", "10", "11", "12", "14", "15", "19", "20", "21", "23"]
sa_1642 = full_col(["16.42"] + sa_1642_pat + ["17.26"])
sa_1742_pat = ["45", "46", "47", "48", "49", "51", "53", "54", "55",
               "56", "57", "58", "59", "18.00", "01", "02", "03", "05", "06",
               "08", "09", "10", "11", "12", "14", "15", "19", "20", "21", "23"]
sa_1742 = full_col(["17.42"] + sa_1742_pat + ["18.26"])
sa_1846 = sa_col("18.46", "19.00", "19.27")
sa_2146 = sa_col("21.46", "22.00", "22.27")

sa_columns = [
    {"cells": sa_646},
    {"cells": sa_746},
    {"cells": sa_842},
    {"type": "triangle", "color": "#0089cf"},
    {"type": "interval", "text": "alle 30 Min."},
    {"cells": sa_1642},
    {"cells": sa_1742},
    {"cells": sa_1846},
    {"type": "triangle", "color": "#0089cf"},
    {"type": "interval", "text": "alle 60 Min."},
    {"cells": sa_2146},
]
section_sa = {"title": "Samstag", "color": "#0089cf", "columns": sa_columns}

# ================= SONNTAG / FEIERTAG =================
so_pat = ["49", "50", "51", "52", "53", "55", "57", "58", "59",
          None, "01", "02", "03", "04", "05", "06", "07", "09", "10",
          "11", "12", "13", "14", "15", "17", "18", "21", "22", "23", "25"]


def so_col(hour):
    pat = list(so_pat)
    pat[9] = f"{hour + 1}.00"
    return full_col([f"{hour}.46"] + pat + [f"{hour + 1}.27"])


# Kurzfahrten 8.11, 9.11 (Para -> Marl Mitte)
def so_short(first, lasthour):
    mins = ["12", "13", "14", "15", "17", "18", "21", "22", "23", "25"]
    return short_col([first] + mins + [f"{lasthour}.27"])


so_columns = [
    {"header": "phone", "cells": so_short("8.11", 8)},
    {"header": "phone", "cells": so_short("9.11", 9)},
]
for h in range(9, 22):
    so_columns.append({"cells": so_col(h)})

section_so = {"title": "Sonntag/Feiertag", "color": "#e94e1b", "columns": so_columns}

# ================= ZUSAMMENBAU =================
data = {
    "line": "223",
    "icon": "bus",
    "title": "RE Hbf – Marl-Lenkerbeck – Hüls Süd – Chemiepark Marl – Marl Mitte",
    "accent": "#e2001a",
    "stops": stops,
    "footnote": "[phone] = TaxiBus mind. 30 Min. Voranmeldung unter 02366/186-186 "
                "oder in der Fahrplanauskunft der Vestischen unter www.vestische.de.",
    "blocks": [
        {"sections": [section_mf, section_sa]},
        {"sections": [section_so]},
    ],
}

with open("beispiel_223.json", "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
print("beispiel_223.json geschrieben:", N, "Haltestellen")
