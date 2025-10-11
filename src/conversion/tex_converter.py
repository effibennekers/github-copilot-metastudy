"""TeX -> Markdown conversie via pre-processing + Pandoc Lua-filter."""

import logging
import os
import re
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)


def pre_process_latex(latex_content: str) -> str:
    latex_content = re.sub(r"\\linebreakand", r"\\\\", latex_content)
    latex_content = re.sub(
        r"\\protect\\colorbox{.*?}{.*?}\\s*|\\scriptsize\\s*", r"", latex_content
    )
    latex_content = re.sub(r"\\tabincell{.*?}{((.|\n)*?)}", r"\1", latex_content)
    latex_content = re.sub(r"\\lstinputlisting\[.*?\]{.*?}", r"", latex_content)
    latex_content = re.sub(r"\\mintinline{.*?}{((.|\n)*?)}", r"`\1`", latex_content)
    latex_content = re.sub(
        r"\\end{document}.*?$", r"\\end{document}", latex_content, flags=re.DOTALL
    )
    return latex_content


def _get_lua_filter_path() -> str:
    root = Path(__file__).resolve().parents[2]
    lua_path = root / "src" / "conversion" / "fix_latex.lua"
    return str(lua_path)


def tex_naar_md(arxiv_id: str) -> str:
    tex_dir = Path("data") / "tex"
    md_dir = Path("data") / "md"
    md_dir.mkdir(parents=True, exist_ok=True)

    tex_path = tex_dir / f"{arxiv_id}.tex"
    md_path = md_dir / f"{arxiv_id}.md"

    if not tex_path.exists():
        raise FileNotFoundError(f"TeX bronbestand niet gevonden: {tex_path}")

    raw = tex_path.read_text(encoding="utf-8", errors="ignore")
    processed = pre_process_latex(raw)

    with NamedTemporaryFile(mode="w", delete=False, suffix=".tex", encoding="utf-8") as tmp_tex:
        tmp_tex.write(processed)
        tmp_tex_path = tmp_tex.name

    lua_filter = _get_lua_filter_path()

    cmd = [
        "pandoc",
        "--from=latex+raw_tex",
        "--to=markdown_strict",
        "--wrap=none",
        "--lua-filter",
        lua_filter,
        "--output",
        str(md_path),
        tmp_tex_path,
    ]

    try:
        logger.info("Pandoc TeX->MD: %s -> %s", tex_path, md_path)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug("Pandoc stdout: %s", result.stdout)
        if result.stderr:
            logger.debug("Pandoc stderr: %s", result.stderr)
        return str(md_path)
    except FileNotFoundError as e:
        logger.error("Pandoc niet gevonden: %s", e)
        raise
    except subprocess.CalledProcessError as e:
        logger.error("Pandoc conversie gefaald (exit %s): %s", e.returncode, e.stderr)
        raise
    finally:
        try:
            os.unlink(tmp_tex_path)
        except OSError:
            pass
