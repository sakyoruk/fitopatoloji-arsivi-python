# -*- coding: utf-8 -*-
import re

SEPARATORS = re.compile(r"[;\n,]+")

def split_synonyms(value):
    result=[]; seen=set()
    for item in SEPARATORS.split(value or ""):
        name=" ".join(item.strip().split())
        key=name.casefold()
        if name and key not in seen:
            seen.add(key); result.append(name)
    return result

def scientific_name_suggestion(value):
    value=" ".join((value or "").strip().split())
    if not value:
        return "", []
    parts=value.split(" ")
    suggested=list(parts)
    notes=[]
    if parts and parts[0] and not parts[0][0].isupper():
        suggested[0]=parts[0][0].upper()+parts[0][1:]
        notes.append("Cins adı büyük harfle başlamalıdır.")
    if len(parts)>1 and parts[1] and any(ch.isupper() for ch in parts[1] if ch.isalpha()):
        suggested[1]=parts[1].lower()
        notes.append("Tür epititi küçük harfle yazılmalıdır.")
    if value.endswith('.'):
        notes.append("Bilimsel adın sonunda nokta bulunmamalıdır.")
        suggested[-1]=suggested[-1].rstrip('.')
    return " ".join(suggested), notes
