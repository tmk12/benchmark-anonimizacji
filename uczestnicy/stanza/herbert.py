"""Przypięcie rewizji HerBERT-a (szkielet polskiego modelu `nkjp_bert`): Stanza ładuje go z cache HF po nazwie
(`AutoModel.from_pretrained("allegro/herbert-base-cased")`, rewizja `main`), więc bez przypięcia wynik zależałby od tego,
co akurat leży w cache albo co autor opublikuje później. Tu: pobranie dokładnie tej rewizji, sprawdzenie, że `refs/main`
w cache wskazuje na nią (to z niego korzysta ładowanie), i to samo sprawdzenie po wczytaniu potoku. Niezgodność = jawny błąd."""
from __future__ import annotations

import hashlib
from pathlib import Path

MODEL = "allegro/herbert-base-cased"
REWIZJA = "50e33e0567be0c0b313832314c586e3df0dc2297"
#: SHA-256 wag tej rewizji (nazwa blobu LFS w repozytorium HF = suma SHA-256 pliku).
SHA256_WAG = "d205995436644f5974156fad33ef9dd55d98bb7484918baa65e0fb62b6964a29"
PLIK_WAG = "pytorch_model.bin"


def _sha256(plik: Path) -> str:
    h = hashlib.sha256()
    with open(plik, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def ustaw_ref(hub: Path, model: str = MODEL, rewizja: str = REWIZJA) -> None:
    """`snapshot_download` z pełnym hashem nie zapisuje `refs/main` – na czystym cache ustawiamy go sami."""
    ref = Path(hub) / ("models--" + model.replace("/", "--")) / "refs" / "main"
    if not ref.is_file():
        ref.parent.mkdir(parents=True, exist_ok=True)
        ref.write_text(rewizja, "utf-8")


def sprawdz_cache(hub: Path, model: str = MODEL, rewizja: str = REWIZJA, sha256_wag: str | None = SHA256_WAG) -> None:
    """Migawka `rewizja` jest w cache `hub` (z wagami o sumie `sha256_wag`), a `refs/main` wskazuje właśnie na nią –
    inaczej `RuntimeError`."""
    kat = Path(hub) / ("models--" + model.replace("/", "--"))
    migawka = kat / "snapshots" / rewizja
    if not (migawka / "config.json").is_file():
        raise RuntimeError(f"{model}: brak migawki {rewizja} w cache HF ({kat})")
    if sha256_wag is not None:
        wagi = migawka / PLIK_WAG
        if not wagi.is_file() or _sha256(wagi) != sha256_wag:
            raise RuntimeError(f"{model}: wagi {PLIK_WAG} migawki {rewizja} mają inną sumę SHA-256 niż przypięta")
    ref = kat / "refs" / "main"
    wskazuje = ref.read_text("utf-8").strip() if ref.is_file() else None
    if wskazuje != rewizja:
        raise RuntimeError(f"{model}: refs/main w cache HF wskazuje {wskazuje!r}, a uczestnik wymaga {rewizja} – "
                           "Stanza załadowałaby inną rewizję")


def przypnij() -> None:
    """Pobiera przypiętą rewizję (z cache, gdy już jest) i sprawdza cache. Offline nie jest wymuszany (inne języki mogą
    jeszcze pobierać swoje szkielety); ewentualne przesunięcie `main` w trakcie ładowania wyłapuje `potwierdz`."""
    from huggingface_hub import constants, snapshot_download

    snapshot_download(MODEL, revision=REWIZJA)
    ustaw_ref(Path(constants.HF_HUB_CACHE))
    sprawdz_cache(Path(constants.HF_HUB_CACHE))


def potwierdz() -> None:
    """Powtórzenie sprawdzenia po wczytaniu potoku (cache nie zmienił się w trakcie)."""
    from huggingface_hub import constants

    sprawdz_cache(Path(constants.HF_HUB_CACHE))
