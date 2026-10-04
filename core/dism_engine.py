"""
DISM (Deployment Image Servicing and Management) engine for image extraction, info querying, and driver injection.
"""

import os
import re
import threading
from typing import Optional, Callable, Tuple, List, Dict, Any
from core.system_executor import run_command


def parse_wim_info_output(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parse DISM /Get-WimInfo output supporting both English and Italian Windows localizations.
    Returns a list of dicts with: index, name, description, size_bytes, size_str, display_str.
    """
    editions = []
    current: Dict[str, Any] = {}

    # Regular expressions for multilingual compatibility (English/Italian/Spanish/German/French)
    idx_pattern = re.compile(r'^(?:Index|Indice|Índice)\s*:\s*(\d+)', re.IGNORECASE)
    name_pattern = re.compile(r'^(?:Name|Nome|Nombre)\s*:\s*(.+)', re.IGNORECASE)
    desc_pattern = re.compile(r'^(?:Description|Descrizione|Descripción)\s*:\s*(.+)', re.IGNORECASE)
    size_pattern = re.compile(r'^(?:Size|Dimensioni|Tamaño|Größe|Taille)\s*:\s*([\d\.,\s]+)\s*(?:bytes|byte|b)?', re.IGNORECASE)

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue

        idx_m = idx_pattern.match(line)
        if idx_m:
            if current and "index" in current:
                editions.append(current)
            current = {"index": int(idx_m.group(1)), "name": "", "description": "", "size_bytes": 0, "size_str": ""}
            continue

        if not current:
            continue

        name_m = name_pattern.match(line)
        if name_m:
            current["name"] = name_m.group(1).strip()
            continue

        desc_m = desc_pattern.match(line)
        if desc_m:
            current["description"] = desc_m.group(1).strip()
            continue

        size_m = size_pattern.match(line)
        if size_m:
            raw_size = size_m.group(1).replace(".", "").replace(",", "").replace(" ", "").strip()
            try:
                bytes_val = int(raw_size)
                current["size_bytes"] = bytes_val
                current["size_str"] = f"{bytes_val / (1024 ** 3):.2f} GB"
            except ValueError:
                current["size_str"] = size_m.group(1).strip()
            continue

    if current and "index" in current:
        editions.append(current)

    for ed in editions:
        name = ed.get("name") or f"Edition {ed['index']}"
        size = ed.get("size_str", "")
        ed["display_str"] = f"[{ed['index']}] {name}" + (f" ({size})" if size else "")

    return editions


def extract_wim_xml_metadata(path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Directly parse embedded WIM/ESD XML metadata without needing dism.exe or Administrator rights.
    Works for install.wim, install.esd, custom editions (e.g. Bizarre11, Tiny11), and any language.
    """
    try:
        clean_path = os.path.abspath(path)
        if not os.path.isfile(clean_path):
            return None

        import xml.etree.ElementTree as ET

        with open(clean_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            total_size = f.tell()
            # The XML metadata is placed in the tail of the WIM/ESD file (read up to 15MB)
            read_size = min(total_size, 15 * 1024 * 1024)
            f.seek(total_size - read_size)
            buffer = f.read(read_size)

            start_tag_utf16 = '<WIM>'.encode('utf-16le')
            end_tag_utf16 = '</WIM>'.encode('utf-16le')

            idx = buffer.find(start_tag_utf16)
            if idx != -1:
                end_idx = buffer.rfind(end_tag_utf16)
                if end_idx != -1:
                    xml_raw = buffer[idx:end_idx + len(end_tag_utf16)].decode('utf-16le', errors='ignore')
                else:
                    xml_raw = buffer[idx:].decode('utf-16le', errors='ignore')
            else:
                start_tag_utf8 = b'<WIM>'
                end_tag_utf8 = b'</WIM>'
                idx = buffer.find(start_tag_utf8)
                if idx == -1:
                    return None
                end_idx = buffer.rfind(end_tag_utf8)
                if end_idx != -1:
                    xml_raw = buffer[idx:end_idx + len(end_tag_utf8)].decode('utf-8', errors='ignore')
                else:
                    xml_raw = buffer[idx:].decode('utf-8', errors='ignore')

            root = ET.fromstring(xml_raw)
            editions = []
            for img in root.findall('IMAGE'):
                index = int(img.get('INDEX', 1))
                name = img.findtext('NAME') or f"Edition {index}"
                desc = img.findtext('DESCRIPTION') or ""
                total_bytes = 0
                tb_elem = img.findtext('TOTALBYTES')
                if tb_elem:
                    try:
                        total_bytes = int(tb_elem)
                    except ValueError:
                        pass
                size_str = f"{total_bytes / (1024**3):.2f} GB" if total_bytes > 0 else ""
                editions.append({
                    "index": index,
                    "name": name.strip(),
                    "description": desc.strip(),
                    "size_bytes": total_bytes,
                    "size_str": size_str,
                    "display_str": f"[{index}] {name.strip()}" + (f" ({size_str})" if size_str else "")
                })

            if editions:
                return editions
    except Exception:
        pass
    return None


def get_wim_info(
    wim_path: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Query all available Windows editions/indices in a .wim or .esd file.
    Tries fast direct XML extraction first (no admin elevation required),
    and falls back to DISM /Get-WimInfo if needed.
    Returns: Tuple (list_of_editions, raw_output)
    """
    clean_path = os.path.abspath(wim_path)
    if not os.path.isfile(clean_path):
        return [], f"WIM/ESD image file not found: {clean_path}"

    # 1. Try fast pure-Python XML extraction first (No DISM needed, No admin elevation needed, 0.001s)
    editions = extract_wim_xml_metadata(clean_path)
    if editions:
        if on_line:
            on_line(f"Extracted {len(editions)} edition(s) from metadata (direct read): {clean_path}")
        return editions, ""

    # 2. Fallback to DISM /Get-WimInfo
    cmd = ["dism", "/Get-WimInfo", f"/WimFile:{clean_path}"]
    if on_line:
        on_line(f"[CMD] {' '.join(cmd)}")

    exit_code, output = run_command(cmd, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return [], f"Failed to inspect WIM file (exit code {exit_code}): {output}"

    editions = parse_wim_info_output(output)
    return editions, output


def extract_dism_progress(line: str) -> Optional[float]:
    """Extract progress percentage (0.0 to 100.0) from DISM stdout lines."""
    # Common DISM progress format: [====== 35.4% ======]
    match = re.search(r'\[[=\s]*([\d\.]+)%\s*[=\s]*\]', line)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    # Alternative format: 35.4%
    match_alt = re.search(r'(\d+(?:\.\d+)?)%', line)
    if match_alt:
        try:
            return float(match_alt.group(1))
        except ValueError:
            pass

    return None


def apply_image(
    image_file: str,
    index: int,
    apply_dir: str,
    on_progress: Optional[Callable[[float], None]] = None,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Apply a Windows image (WIM/ESD) to a destination directory/drive.
    Executes: dism /Apply-Image /ImageFile:<path> /Index:<index> /ApplyDir:<dir>
    """
    clean_image = os.path.abspath(image_file)
    clean_apply = os.path.abspath(apply_dir)
    if not clean_apply.endswith("\\"):
        clean_apply += "\\"

    if not os.path.isfile(clean_image):
        return False, f"Image file not found: {clean_image}"

    cmd = [
        "dism",
        "/Apply-Image",
        f"/ImageFile:{clean_image}",
        f"/Index:{index}",
        f"/ApplyDir:{clean_apply}"
    ]

    if on_line:
        on_line(f"[CMD] {' '.join(cmd)}")

    def handle_line(line: str):
        if on_line:
            on_line(line)
        if on_progress:
            prog = extract_dism_progress(line)
            if prog is not None:
                on_progress(prog)

    exit_code, output = run_command(
        cmd,
        on_line=handle_line,
        cancel_event=cancel_event
    )

    if exit_code != 0:
        return False, f"DISM Apply-Image failed (code {exit_code}): {output}"

    if on_progress:
        on_progress(100.0)

    return True, "Windows image successfully applied."


def add_drivers(
    image_dir: str,
    driver_folder: str,
    on_line: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[bool, str]:
    """
    Inject third-party device drivers into the offline Windows image.
    Executes: dism /Image:<image_dir> /Add-Driver /Driver:<driver_folder> /Recurse
    """
    clean_image = os.path.abspath(image_dir)
    if not clean_image.endswith("\\"):
        clean_image += "\\"

    clean_drivers = os.path.abspath(driver_folder)
    if not os.path.isdir(clean_drivers):
        return False, f"Driver directory not found: {clean_drivers}"

    cmd = [
        "dism",
        f"/Image:{clean_image}",
        "/Add-Driver",
        f"/Driver:{clean_drivers}",
        "/Recurse"
    ]

    if on_line:
        on_line(f"[CMD] {' '.join(cmd)}")

    exit_code, output = run_command(cmd, on_line=on_line, cancel_event=cancel_event)
    if exit_code != 0:
        return False, f"Failed to inject drivers (code {exit_code}): {output}"

    return True, "Drivers successfully injected into offline image."
