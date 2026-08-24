# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

project_root = Path(SPECPATH).parent

datas, binaries, hiddenimports = [], [], []
for package in ("faster_whisper", "ctranslate2", "tokenizers", "llama_cpp", "huggingface_hub"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(project_root / "packaging" / "launcher.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["torch", "tensorflow", "matplotlib", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="LocalScribe",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="LocalScribe")
