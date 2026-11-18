"""Atrapa uczestnika: protokół JSONL na stdin/stdout, tryby sterowane zmienną `ATRAPA_TRYB` (zob. KONFIG.md)."""
import json
import os
import platform
import shutil
import sys
import time
import zipfile

TRYB = os.environ.get("ATRAPA_TRYB", "idealny")
IDY = {i for i in os.environ.get("ATRAPA_ID", "").split(",") if i}


def wyslij(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def dotyczy(id_dok):
    return not IDY or id_dok in IDY


_MANIFEST = {}


def gold_manifestu(id_dok):
    if not _MANIFEST:
        with open(os.environ["ATRAPA_MANIFEST"], encoding="utf-8") as f:
            for linia in f:
                if linia.strip():
                    wpis = json.loads(linia)
                    _MANIFEST[wpis["id"]] = wpis
    return _MANIFEST[id_dok]


def zamaz(dane, teksty):
    for t in sorted(teksty, key=len, reverse=True):
        if t:
            dane = dane.replace(t.encode("utf-8"), b"x" * len(t.encode("utf-8")))
    return dane


def kopiuj_zamazujac(wej, wyj, teksty):
    if zipfile.is_zipfile(wej):
        with zipfile.ZipFile(wej) as z, zipfile.ZipFile(wyj, "w", zipfile.ZIP_DEFLATED) as o:
            for info in z.infolist():
                o.writestr(info, zamaz(z.read(info), teksty))
    else:
        with open(wej, "rb") as f, open(wyj, "wb") as o:
            o.write(zamaz(f.read(), teksty))


def obsluz(zad):
    id_dok = zad["id"]
    if "tekst" in zad:
        if TRYB == "wolny" and dotyczy(id_dok):
            if os.environ.get("ATRAPA_PID_PLIK"):          # proces potomny (jak serwer modelu) – test zabijania drzewa
                import subprocess
                dziecko = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
                with open(os.environ["ATRAPA_PID_PLIK"], "w") as f:
                    f.write(str(dziecko.pid))
            time.sleep(float(os.environ.get("ATRAPA_SEN", "3600")))
        if TRYB == "pada" and dotyczy(id_dok):
            os._exit(3)
        if TRYB == "zle_offsety" and dotyczy(id_dok):
            n = len(zad["tekst"])
            return {"id": id_dok, "wykrycia": [[n + 5, n + 9, "X", 1.0]]}
        if TRYB in ("pusty", "plik_kopia"):
            return {"id": id_dok, "wykrycia": []}
        gold = gold_manifestu(id_dok)["gold_tekst"]
        return {"id": id_dok, "wykrycia": [[g["start"], g["end"], g["kategoria"], 1.0] for g in gold]}
    if TRYB == "inne_rozszerzenie":                 # R38: narzędzie zapisuje wynik w innym formacie niż oryginał (jak .msg → .txt)
        cel = os.path.splitext(zad["plik_wyj"])[0] + ".txt"
        with open(cel, "w", encoding="utf-8") as f:
            f.write("zanonimizowana tresc\n")
        return {"id": id_dok, "plik_wyj": cel}
    if TRYB == "idealny" or (TRYB in ("wolny", "pada", "zle_offsety") and not dotyczy(id_dok)):
        wpis = gold_manifestu(id_dok)
        teksty = [g["tekst"] for g in wpis["gold_plik"]]
        kopiuj_zamazujac(zad["plik_wej"], zad["plik_wyj"], teksty)
    else:
        shutil.copyfile(zad["plik_wej"], zad["plik_wyj"])
    return {"id": id_dok, "plik_wyj": zad["plik_wyj"]}


def main():
    wyslij({"gotowy": True, "wersje": {"atrapa": "0.1", "python": platform.python_version()}})
    for linia in sys.stdin:
        if linia.strip():
            wyslij(obsluz(json.loads(linia)))


if __name__ == "__main__":
    main()
