# -*- coding: utf-8 -*-
"""Zengin metin biçimlerini Tk, HTML ve ReportLab çıktılarına dönüştürür."""
from __future__ import print_function
import html
import re


def index_to_offset(text, index):
    """Tk 'satır.sütun' indeksini karakter konumuna çevirir."""
    try:
        line_s, col_s = str(index).split('.', 1)
        line = max(1, int(line_s))
        col = max(0, int(col_s))
    except (TypeError, ValueError):
        return 0
    lines = text.splitlines(True)
    if line > len(lines):
        return len(text)
    return min(len(text), sum(len(item) for item in lines[:line - 1]) + col)


def offset_to_index(text, offset):
    offset = max(0, min(len(text), int(offset)))
    before = text[:offset]
    line = before.count('\n') + 1
    col = len(before.rsplit('\n', 1)[-1])
    return '{}.{}'.format(line, col)


def formatting_spans(text, formatting):
    spans = []
    for item in (formatting or {}).get('tags', []):
        name = item.get('name', '')
        color = item.get('color')
        for start, end in item.get('ranges', []):
            a = index_to_offset(text, start)
            b = index_to_offset(text, end)
            if b > a:
                spans.append((a, b, name, color))
    return spans


def apply_to_text_widget(widget, text, formatting, base_index='1.0', font_size=9):
    """Biçimleri, birleşik kalın+italik durumları da korunacak şekilde uygular."""
    widget.tag_configure('rt_bold', font=('Segoe UI', font_size, 'bold'))
    widget.tag_configure('rt_italic', font=('Segoe UI', font_size, 'italic'))
    widget.tag_configure('rt_bold_italic', font=('Segoe UI', font_size, 'bold italic'))
    widget.tag_configure('rt_underline', underline=True)
    spans = formatting_spans(text, formatting)
    boundaries = {0, len(text)}
    for a, b, _name, _color in spans:
        boundaries.add(a); boundaries.add(b)
    points = sorted(boundaries)
    base_line, base_col = [int(x) for x in str(base_index).split('.', 1)]

    def shifted_index(offset):
        local = offset_to_index(text, offset)
        line, col = [int(x) for x in local.split('.', 1)]
        if line == 1:
            return '{}.{}'.format(base_line, base_col + col)
        return '{}.{}'.format(base_line + line - 1, col)

    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if b <= a:
            continue
        active = [(name, color) for sa, sb, name, color in spans if sa <= a and sb >= b]
        names = {name for name, _color in active}
        start, end = shifted_index(a), shifted_index(b)
        if 'bold' in names and 'italic' in names:
            widget.tag_add('rt_bold_italic', start, end)
        elif 'bold' in names:
            widget.tag_add('rt_bold', start, end)
        elif 'italic' in names:
            widget.tag_add('rt_italic', start, end)
        if 'underline' in names:
            widget.tag_add('rt_underline', start, end)
        for name, color in active:
            if name.startswith('color_'):
                value = color or ('#' + name.split('_', 1)[1])
                tag = 'rt_' + name
                widget.tag_configure(tag, foreground=value)
                widget.tag_add(tag, start, end)


def _segments(text, formatting):
    spans = formatting_spans(text, formatting)
    boundaries = {0, len(text)}
    for a, b, _name, _color in spans:
        boundaries.add(a); boundaries.add(b)
    points = sorted(boundaries)
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        if b <= a:
            continue
        active = [(name, color) for sa, sb, name, color in spans if sa <= a and sb >= b]
        yield text[a:b], active


def to_html(text, formatting):
    chunks = []
    for segment, active in _segments(text or '', formatting or {}):
        value = html.escape(segment).replace('\n', '<br>')
        names = {name for name, _color in active}
        color = next((c or ('#' + n.split('_', 1)[1]) for n, c in active if n.startswith('color_')), None)
        if color:
            value = "<span style='color:{}'>".format(html.escape(color, quote=True)) + value + '</span>'
        if 'underline' in names:
            value = '<u>' + value + '</u>'
        if 'italic' in names:
            value = '<i>' + value + '</i>'
        if 'bold' in names:
            value = '<b>' + value + '</b>'
        chunks.append(value)
    return ''.join(chunks)


def to_reportlab(text, formatting):
    """ReportLab Paragraph tarafından desteklenen güvenli işaretleme."""
    chunks = []
    for segment, active in _segments(text or '', formatting or {}):
        value = (segment.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                 .replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br/>'))
        names = {name for name, _color in active}
        color = next((c or ('#' + n.split('_', 1)[1]) for n, c in active if n.startswith('color_')), None)
        if color and re.match(r'^#[0-9A-Fa-f]{6}$', color):
            value = '<font color="{}">'.format(color) + value + '</font>'
        if 'underline' in names:
            value = '<u>' + value + '</u>'
        if 'italic' in names:
            value = '<i>' + value + '</i>'
        if 'bold' in names:
            value = '<b>' + value + '</b>'
        chunks.append(value)
    return ''.join(chunks)
