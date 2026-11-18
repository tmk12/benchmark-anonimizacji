"""Uczestnik `openai-privacy-filter`: wyłącznie `openai/privacy-filter` (HF, zweryfikowana organizacja OpenAI) uruchamiany
oficjalnym pakietem `opf` (github.com/openai/privacy-filter, commit przypięty w pyproject.toml) z dekodowaniem Viterbiego.

Konfiguracja wg autorów: wagi z podkatalogu `original/` repozytorium HF (format `opf`), tokenizer tiktoken `o200k_base`, dekoder
Viterbiego z `viterbi_calibration.json` (punkt pracy `default`, wszystkie biasy 0), przycinanie białych znaków ze spanów, CPU.
Różnica wobec `opf.OPF.redact`: tekst dzielony jest na okna tokenowe z zakładką (rozstrzygnięcie 3; `opf` tnie bez zakładki),
a każdy wykryty span dostaje wynik (średnie prawdopodobieństwo przypisanych tagów BIOES), którego `opf` nie zwraca – potrzebny
do kalibracji. Szczegóły: KONFIG.md."""
from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
KORZEN = KATALOG.parent.parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

# Słownik tiktoken (`o200k_base`, plik z publicznego magazynu OpenAI) trafia do vendor/ i jest czytany stamtąd offline.
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(KORZEN / "vendor" / "tiktoken"))

import okna  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MODEL = "openai/privacy-filter"
REWIZJA = "7ffa9a043d54d1be65afb281eddf0ffbe629385b"
KOMMIT_OPF = "f7f00ca7fb869683eb732c010299d901457f19c3"
# Domyślne `n_ctx` pakietu `opf` na CPU (`_resolve_n_ctx`); karta: 128 000 tokenów (GPU). Uwaga modelu jest pasmowa (±128
# tokenów), więc okno 4096 z zakładką daje wynik jak na całym tekście.
OKNO_TOKENOW = 4096
ZAKLADKA = 0.125                       # >= 10% (rozstrzygnięcie 3)
PROG_DOMYSLNY = 0.0                    # autorzy: twarde dekodowanie Viterbiego, bez progu; wynik własny służy kalibracji


def _okno_tokenow() -> int:
    """Rozmiar okna w tokenach; `PBENCH_OKNO_TOKENOW` (testy granicy okna) nadpisuje."""
    return int(os.environ.get("PBENCH_OKNO_TOKENOW", OKNO_TOKENOW))


def _wersja(pakiet: str) -> str:
    try:
        return metadata.version(pakiet)
    except metadata.PackageNotFoundError:
        return "?"


def _pobierz() -> str:
    """Katalog `original/` migawki repozytorium z przypiętej rewizji (tylko pliki potrzebne `opf`, bez ONNX)."""
    from huggingface_hub import snapshot_download
    s = snapshot_download(MODEL, revision=REWIZJA, allow_patterns=["original/*", "*.json", "README.md"])
    return str(Path(s) / "original")


def _zainstaluj_szybkie_moe() -> None:
    """Zastępuje na CPU referencyjną warstwę MoE `opf` (dla każdego tokenu kopiuje wagi 4 ekspertów i mnoży przez `bmm`; ~100-400 s
    na dokument ~600 tokenów) wersją liczącą to samo w float32, ale zgrupowaną po ekspertach (jedno `matmul` na eksperta).
    Model, wagi, bramka, SwiGLU, wagi ekspertów i zaokrąglenie wyjścia jak w oryginale; różni się tylko kolejność sumowania.
    `PBENCH_MOE_ORYGINAL=1` zostawia kod autorów (test równoważności)."""
    if os.environ.get("PBENCH_MOE_ORYGINAL") == "1":
        return
    import torch
    import torch.nn.functional as F
    from opf._model import model as m

    def forward(self, x):
        if x.dim() != 3:
            raise ValueError("MLPBlock expects batched 3D tensor input")
        batch_shape = x.shape[:-1]
        t = self.norm(x).reshape(-1, x.shape[-1])
        g = F.linear(t.float(), self.gate.weight.float(), self.gate.bias.float())
        eks = torch.topk(g, k=self.experts_per_token, dim=-1, sorted=True)
        wagi = F.softmax(eks.values, dim=1) / self.experts_per_token
        idx = eks.indices
        k = self.experts_per_token
        tf = t.float()
        wyj = torch.zeros(tf.shape, dtype=torch.float32)
        plaskie = idx.reshape(-1)
        kolejnosc = torch.argsort(plaskie, stable=True)
        liczby = torch.bincount(plaskie, minlength=self.num_experts).tolist()
        poz = 0
        for e, n in enumerate(liczby):
            if n == 0:
                continue
            sel = kolejnosc[poz:poz + n]
            poz += n
            tok = sel // k
            h = tf[tok] @ self.mlp1_weight[e].float() + self.mlp1_bias[e].float()
            h = m.swiglu(h, limit=self.swiglu_limit, packed=self.packed_geglu)
            h = h @ self.mlp2_weight[e].float() + self.mlp2_bias[e].float()
            wyj.index_add_(0, tok, h * wagi.reshape(-1)[sel][:, None])
        wyj = wyj * k
        return x + wyj.to(x.dtype).reshape(*batch_shape, -1)

    m.MLPBlock.forward = forward


def zbuduj(prog: float):
    """Model, dekoder i `analizuj(tekst, jezyk)` → wykrycia ≥ `prog`; zwraca (analizuj, wersje). Tej samej funkcji używa
    wariant krzyżowy `privatizer-tekst-opf` (detektor w potoku Privatizera)."""
    import torch
    import torch.nn.functional as F
    from opf._core.decoding import build_sequence_decoder
    from opf._core.runtime import load_inference_runtime
    from opf._core.spans import decode_text_with_offsets, labels_to_spans, token_spans_to_char_spans, trim_char_spans_whitespace

    _zainstaluj_szybkie_moe()
    runtime = load_inference_runtime(checkpoint=_pobierz(), device_name="cpu", n_ctx_override=OKNO_TOKENOW,
                                     trim_span_whitespace=True, discard_overlapping_predicted_spans=False,
                                     output_mode="typed")
    dekoder, _ = build_sequence_decoder(decode_mode="viterbi", label_info=runtime.label_info,
                                        viterbi_calibration_path=None, checkpoint_dir=runtime.checkpoint)
    nazwy = list(runtime.label_info.span_class_names)
    wersje = {"opf": _wersja("opf"), "opf:commit": KOMMIT_OPF, "torch": _wersja("torch"), "tiktoken": _wersja("tiktoken"),
              "hf:model": f"{MODEL}@{REWIZJA}", "dekodowanie": "viterbi (viterbi_calibration.json: default)",
              "moe": "oryginal opf" if os.environ.get("PBENCH_MOE_ORYGINAL") == "1" else "zgrupowane po ekspertach (float32)"}

    @torch.inference_mode()
    def logprob_tokenow(tokeny: list[int]) -> torch.Tensor:
        """Log-prawdopodobieństwa klas każdego tokenu z okien z zakładką; token bierze okno, w którym leży dalej od krawędzi."""
        ok = okna.okna_indeksowe(len(tokeny), _okno_tokenow(), ZAKLADKA)
        wyniki = None
        for (a, b), (od, do) in zip(ok, okna.zakresy_wlasne(ok)):
            wej = torch.tensor([tokeny[a:b]], dtype=torch.int32, device=runtime.device)
            lp = F.log_softmax(runtime.model(wej, attention_mask=torch.ones_like(wej, dtype=torch.bool)).float(), dim=-1)[0].cpu()
            if wyniki is None:
                wyniki = torch.empty((len(tokeny), lp.shape[1]))
            wyniki[od:do] = lp[od - a:do - a]
        return wyniki

    def analizuj(tekst: str, jezyk: str) -> list:
        tokeny = [int(t) for t in runtime.encoding.encode(tekst, allowed_special="all")]
        if not tokeny:
            return []
        lp = logprob_tokenow(tokeny)
        etykiety = dekoder.decode(lp)
        if len(etykiety) != len(tokeny):
            etykiety = lp.argmax(dim=1).tolist()
        przypisane = {i: int(e) for i, e in enumerate(etykiety)}
        zdekodowany, pocz, kon = decode_text_with_offsets(tokeny, runtime.encoding)
        # Jak w `opf` (`decoded_mismatch`): tiktoken zamienia niesparowane surrogaty na U+FFFD, więc zdekodowany tekst może się różnić
        # od wejścia znakami, ale ma tę samą długość w znakach – offsety zostają dokładne. Inna długość = realny błąd (nie maskujemy).
        if len(zdekodowany) != len(tekst):
            raise ValueError(f"tokenizer zmienia długość tekstu ({len(tekst)} -> {len(zdekodowany)} znaków)")
        prawd = lp.exp()
        wynik = []
        for idx, t0, t1 in labels_to_spans(przypisane, runtime.label_info):
            sc = float(sum(prawd[i, przypisane[i]] for i in range(t0, t1)) / (t1 - t0))
            znakowe = trim_char_spans_whitespace(token_spans_to_char_spans([(idx, t0, t1)], pocz, kon), tekst)
            wynik += [(s, e, nazwy[idx] if 0 <= idx < len(nazwy) else f"label_{idx}", sc) for _, s, e in znakowe]
        return [w for w in sorted(wynik) if w[3] >= prog]

    return analizuj, wersje


def main() -> None:
    pu.ustaw_watki()
    analizuj, wersje = zbuduj(pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY))
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
