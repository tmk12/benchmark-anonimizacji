"""Offsety wartości wzorcowej w przykładach raportu (`przyklady.jsonl`) – do podświetlenia wycieku w tabeli „Przykłady”.

    python narzedzia/zakresy_przykladow.py --przyklady przyklady.jsonl --korpus korpus --cel raport/dane/przyklady_zakresy.json

`pbench.agregacja._przyklady` zapisuje okno tekstu wokół pierwszej wyciekłej wartości (80 znaków przed i po jej spanie gold), ale nie
zapisuje pozycji wartości w oknie. Skrypt odtwarza ją z manifestu korpusu (span gold o `wartosc_id` z pola `wyciek`) i sprawdza, że okno
z korpusu jest równe polu `przed` – inaczej przerywa. Wyjście: `{"<id>|<wartosc_id>": {"od", "do", "tekst"}}` (offsety w `przed`);
korpus jest syntetyczny. Kod agregacji i wyniki nie są zmieniane."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OKNO = 80  # tyle samo, co w `pbench.agregacja._przyklady`


def zakresy(przyklady: list[dict], korpus: Path) -> dict[str, dict]:
    manifest = {w["id"]: w for w in (json.loads(l) for l in (korpus / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    wynik: dict[str, dict] = {}
    for p in przyklady:
        wpis, wid = manifest[p["id"]], p["wyciek"][0]
        span = next((g for g in wpis["gold_tekst"] if g["wartosc_id"] == wid), None)
        if span is None:
            raise SystemExit(f"Brak wartości wzorcowej {wid} w gold_tekst dokumentu {p['id']} (przykład niezgodny z manifestem korpusu)")
        tekst = (korpus / wpis["plik_txt"]).read_bytes().decode("utf-8")
        a, b = max(0, span["start"] - OKNO), min(len(tekst), span["end"] + OKNO)
        if tekst[a:b] != p["przed"]:
            raise SystemExit(f"{p['id']}: okno z korpusu różni się od pola „przed” – zły korpus albo zmieniony format przykładów")
        wynik[f"{p['id']}|{wid}"] = {"od": span["start"] - a, "do": span["end"] - a, "tekst": span["tekst"]}
    return wynik


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--przyklady", type=Path, required=True, help="przyklady.jsonl z agregacji")
    ap.add_argument("--korpus", type=Path, required=True, help="katalog korpusu (manifest.jsonl i pliki .txt)")
    ap.add_argument("--cel", type=Path, required=True, help="plik JSON wynikowy")
    a = ap.parse_args(argv)
    przyklady = [json.loads(l) for l in a.przyklady.read_text(encoding="utf-8").splitlines() if l.strip()]
    wynik = zakresy(przyklady, a.korpus)
    a.cel.parent.mkdir(parents=True, exist_ok=True)
    a.cel.write_text(json.dumps(wynik, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: {len(wynik)} zakresów -> {a.cel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
