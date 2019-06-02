#!/usr/bin/env python3

import os
import sys

import yaml

from escrutinio import Escrutinio

file = sys.argv[1] if len(sys.argv) > 1 else None

if file is None or not os.path.isfile(file):
    sys.exit("Ha de pasar un fichero de circunscripciones por parámetro")

izq = '''
ADELANTE ANDALUCIA
EQUO-INICIATIVA
EB
'''.strip().split("\n")

escrutinio = Escrutinio(file)
escrutinio.seats(show=True, detail=True)
# print("\n".join(sorted(escrutinio.partidos)))
for c in escrutinio.circunscripciones:
    keys = [k for k in c.partidos.keys() if k != "VOX"]
    plus = int(c.abstencion * (50/100) / len(keys))
    for k in keys:
        c.partidos[k] = c.partidos[k]+plus
# escrutinio.seats(show=True)
print("")
escrutinio.reset()
escrutinio.join(
    #    ['PSOE-A']+izq,
    ["VOX", "FE de las JONS"]
)
escrutinio.seats(show=True, detail=True)
escrutinio.reset()
print("")
escrutinio.join("ADELANTE ANDALUCIA", blancos=True,
                nulos=True, abstencion=5/100)
escrutinio.seats(show=True, detail=True)
