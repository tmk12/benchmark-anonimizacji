"""Renderery dokumentów (DOCX, PDF, skan, poczta…)."""
from __future__ import annotations

import contextlib
from collections.abc import Iterator

from reportlab import rl_config


@contextlib.contextmanager
def bez_a85() -> Iterator[None]:
    """Reportlab koduje strumienie (treść stron, obrazy, czcionki) ASCII85 albo nie, zależnie od GLOBALNEJ flagi
    `rl_config.useA85` (domyślnie 1). Każdy zapis pliku korpusu przez reportlab (renderer PDF, skan, operacje warstwy trudnych
    przypadków) idzie w tym bloku: bez ASCII85, więc bajty nie zależą od tego, co zrobił inny kod w procesie. Flaga wraca potem
    do poprzedniej wartości – nie zmieniamy jej globalnie (np. `canvas.drawInlineImage` z `useA85 = 0` kończy się błędem
    bytes/str w reportlabie)."""
    stara = rl_config.useA85
    rl_config.useA85 = 0
    try:
        yield
    finally:
        rl_config.useA85 = stara
