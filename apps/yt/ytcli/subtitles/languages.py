from __future__ import annotations

from ..models import SubtitleTracks


def resolve_subtitle_langs(
    requested: tuple[str, ...],
    tracks: SubtitleTracks,
    auto_subs: bool = True,
) -> tuple[list[str], list[str]]:
    """Map requested languages onto codes the video really has, returning (codes, warnings).

    Asking yt-dlp for a pattern such as ``en.*`` also pulls YouTube's machine-translated
    tracks (``en-de``, ``en-fr``, ...), which is both unwanted and a fast route to HTTP 429.
    Resolving against the real track list keeps every request exact.
    """
    available = list(dict.fromkeys(tracks.manual + (tracks.automatic if auto_subs else ())))
    if "all" in requested:
        return (available, []) if available else ([], ["this video has no subtitles"])

    codes: list[str] = []
    warnings: list[str] = []
    for lang in requested:
        match = best_match(lang, available)
        if match is None:
            warnings.append(
                f"no {lang} subtitles (available: {', '.join(available) if available else 'none'})"
            )
        elif match not in codes:
            codes.append(match)
    return codes, warnings


def best_match(lang: str, available: list[str]) -> str | None:
    """Prefer an exact code, then '<lang>-orig', then the shortest regional variant."""
    wanted = lang.lower()
    by_lower = {code.lower(): code for code in available}
    if wanted in by_lower:
        return by_lower[wanted]
    prefixed = [code for code in available if code.lower().split("-")[0] == wanted]
    if not prefixed:
        return None
    return sorted(prefixed, key=lambda code: (code.lower() != f"{wanted}-orig", len(code), code))[0]
