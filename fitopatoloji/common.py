# -*- coding: utf-8 -*-
"""Fitopatoloji Arşivi - Windows 7 uyumlu yerel masaüstü arşivi.

Yalnızca Python standart kütüphanesini kullanır: tkinter + sqlite3.
PyInstaller ile paketlendiğinde hedef bilgisayarda Python kurulumu gerekmez.
"""
from __future__ import print_function

import csv
import json
import hashlib

# Bazı yeni kütüphaneler hashlib oluşturucularına "usedforsecurity"
# parametresi gönderir. Windows 7 için kullanılan Python 3.8'in bazı
# derlemeleri bu parametreyi kabul etmez.
def _make_hashlib_compatible(name):
    original = getattr(hashlib, name, None)
    if original is None:
        return
    try:
        original(b"", usedforsecurity=False)
        return
    except TypeError:
        pass

    def compatible(data=b"", *args, **kwargs):
        kwargs.pop("usedforsecurity", None)
        return original(data, *args, **kwargs)

    setattr(hashlib, name, compatible)

for _hash_name in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512"):
    _make_hashlib_compatible(_hash_name)
del _hash_name

import datetime as dt
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile
from xml.sax.saxutils import escape as xml_escape

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
except ImportError:  # pragma: no cover
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import tkSimpleDialog as simpledialog
    import ttk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle
    )
    import reportlab
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

APP_NAME = "Fitopatoloji Arşivi"
APP_VERSION = "2.0.0 RC6.1"

LONG_FIELDS = [
    ("hosts", "Konukçular"),
    ("affected_organs", "Etkilenen organlar"),
    ("symptoms", "Belirtiler"),
    ("pathogen_features", "Etmenin özellikleri"),
    ("disease_cycle", "Hastalık döngüsü"),
    ("epidemiology", "Epidemiyoloji / uygun çevre koşulları"),
    ("differential_diagnosis", "Ayırıcı teşhis"),
    ("cultural_control", "Kültürel mücadele"),
    ("biological_control", "Biyolojik mücadele"),
    ("chemical_control", "Kimyasal mücadele / prensipler"),
    ("distribution_turkey", "Türkiye dağılımı"),
    ("distribution_world", "Dünya dağılımı"),
    ("climate_notes", "İklim / çevre notları"),
    ("sources", "Kaynaklar"),
    ("notes", "Kişisel notlar"),
]

ALL_DB_FIELDS = [
    "id", "group_name", "scientific_name", "synonyms", "disease_name",
    "hosts", "affected_organs", "symptoms", "pathogen_features",
    "disease_cycle", "epidemiology", "differential_diagnosis",
    "cultural_control", "biological_control", "chemical_control",
    "distribution_turkey", "distribution_world", "climate_notes",
    "sources", "notes", "favorite", "created_at", "updated_at", "deleted_at",
    "agent_group", "domain_name", "kingdom_name", "phylum_name", "subphylum_name",
    "class_name", "order_name", "family_name", "genus_name", "species_name",
    "subspecies_name", "pathovar", "forma_specialis", "strain_name", "isolate_name",
    "taxonomy_source", "taxonomy_accessed_at", "taxonomy_notes",
]


def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """Paket içindeki salt-okunur kaynaklara ulaşır."""
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS, *parts))
    candidates.append(os.path.join(app_base_dir(), *parts))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


class AppPaths(object):
    def __init__(self, base_dir=None):
        self.base = os.path.abspath(base_dir or app_base_dir())
        self.data = os.path.join(self.base, "Data")
        self.images = os.path.join(self.base, "Images")
        self.documents = os.path.join(self.base, "Documents")
        self.backups = os.path.join(self.base, "Backups")
        self.exports = os.path.join(self.base, "Exports")
        self.database = os.path.join(self.data, "fitopatoloji.db")
        for folder in (self.data, self.images, self.documents, self.backups, self.exports):
            if not os.path.isdir(folder):
                os.makedirs(folder)


