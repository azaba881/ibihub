#!/usr/bin/env python3
"""Replace relative asset paths with {% static %} and key internal links with {% url %}."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = [
    ROOT / "templates" / "public",
    ROOT / "templates" / "dashboard",
    ROOT / "templates" / "email",
]


def ensure_load_static(text: str) -> str:
    if "{% load static %}" in text:
        return text
    if "{% static " not in text and "{% url " not in text:
        return text
    if text.strip().startswith("{% extends"):
        lines = text.split("\n")
        out = []
        for i, line in enumerate(lines):
            out.append(line)
            if i == 0 and "{% extends" in line:
                out.append("{% load static %}")
        return "\n".join(out)
    if text.strip().startswith("<!DOCTYPE"):
        parts = text.split("\n", 1)
        return parts[0] + "\n{% load static %}\n" + (parts[1] if len(parts) > 1 else "")
    return "{% load static %}\n" + text


def _static_attr(prefix: str, path: str) -> str:
    return f'{prefix}="{{% static \'{path}\' %}}"'


def patch_assets(text: str) -> str:
    # Dashboard / nested paths
    text = re.sub(r'href="\.\./css/([^"]+)"', lambda m: _static_attr("href", f"css/{m.group(1)}"), text)
    text = re.sub(r'src="\.\./css/([^"]+)"', lambda m: _static_attr("src", f"css/{m.group(1)}"), text)
    text = re.sub(r'href="\.\./images/([^"]+)"', lambda m: _static_attr("href", f"images/{m.group(1)}"), text)
    text = re.sub(r'src="\.\./images/([^"]+)"', lambda m: _static_attr("src", f"images/{m.group(1)}"), text)
    text = re.sub(r'src="\.\./scripts/([^"]+)"', lambda m: _static_attr("src", f"js/{m.group(1)}"), text)
    text = re.sub(r'href="\.\./fonts/([^"]+)"', lambda m: _static_attr("href", f"fonts/{m.group(1)}"), text)
    # Root-relative (public pages)
    text = re.sub(r'href="css/([^"]+)"', lambda m: _static_attr("href", f"css/{m.group(1)}"), text)
    text = re.sub(r'src="css/([^"]+)"', lambda m: _static_attr("src", f"css/{m.group(1)}"), text)
    text = re.sub(r'href="images/([^"]+)"', lambda m: _static_attr("href", f"images/{m.group(1)}"), text)
    text = re.sub(r'src="images/([^"]+)"', lambda m: _static_attr("src", f"images/{m.group(1)}"), text)
    text = re.sub(r'src="scripts/([^"]+)"', lambda m: _static_attr("src", f"js/{m.group(1)}"), text)
    text = re.sub(r'href="fonts/([^"]+)"', lambda m: _static_attr("href", f"fonts/{m.group(1)}"), text)
    return text


def patch_urls(text: str) -> str:
    def home_repl(m: re.Match) -> str:
        frag = m.group(1) or ""
        return f'href="{{% url \'core:home\' %}}{frag}"'

    def espaces_repl(m: re.Match) -> str:
        frag = m.group(1) or ""
        return f'href="{{% url \'core:liste_espaces\' %}}{frag}"'

    text = re.sub(r'href="index\.html(#[^"]*)?"', home_repl, text)
    text = re.sub(r'href="espaces\.html(#[^"]*)?"', espaces_repl, text)
    text = re.sub(
        r'action="espaces\.html(#[^"]*)?"',
        lambda m: f'action="{{% url \'core:liste_espaces\' %}}{m.group(1) or ""}"',
        text,
    )
    text = re.sub(
        r'href="dashboard-user\.html(#[^"]*)?"',
        lambda m: f'href="{{% url \'core:mon_dashboard\' %}}{m.group(1) or ""}"',
        text,
    )
    return text


def process_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    if "{% static 'css/" in raw and "href=\"css/" not in raw and "href=\"../css/" not in raw:
        # likely already patched
        pass
    out = patch_assets(raw)
    out = patch_urls(out)
    out = ensure_load_static(out)
    if out != raw:
        path.write_text(out, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for d in DIRS:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.html")):
            if process_file(path):
                changed += 1
                print("patched:", path.relative_to(ROOT))
    print(f"Total files updated: {changed}")


if __name__ == "__main__":
    main()
