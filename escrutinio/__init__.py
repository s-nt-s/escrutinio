import yaml
from bunch import Bunch

from .dhondt import dhondt


def load(file):
    with open(file, "r") as f:
        r = yaml.safe_load_all(f)
        return [Bunch(**i) for i in r]


class Escrutinio:
    def __init__(self, file, limite=3):
        self._circunscripciones = load(file)
        self._limite = limite
        self.circunscripciones = None
        self.limite = None
        self.partidos = None
        self.reset()

    def reset(self):
        self.circunscripciones = self._circunscripciones.copy()
        self.limite = self._limite
        self.partidos = set()
        for c in self.circunscripciones:
            for p in c.partidos:
                self.partidos.add(p)

    def join(self, *args, blancos=False, nulos=False, abstencion=0):
        for c in self.circunscripciones:
            for i, ps in enumerate(args):
                if isinstance(ps, str):
                    ps = [ps]
                ini = ps[0]
                if ini in c.partidos:
                    if i == 0:
                        if blancos:
                            c.partidos[ini] = c.partidos[ini] + c.blancos
                        if nulos:
                            c.partidos[ini] = c.partidos[ini] + c.nulos
                        if abstencion:
                            c.partidos[ini] = c.partidos[ini] + \
                                int(c.abstencion*abstencion)
                    for p in ps[1:]:
                        if p in c.partidos:
                            c.partidos[ini] = c.partidos[ini]+c.partidos[p]
                            del c.partidos[p]

    def seats(self, show=False, detail=False):
        total = {}
        limite = float(self.limite)
        for c in self.circunscripciones:
            result = dhondt(c.diputados, limite, c.partidos, blankv=c.blancos)
            if detail:
                repe = sorted([(k, v) for k, v in result.repre.items(
                ) if v > 0], key=lambda p: p[0], reverse=True)
                print('  {1:2}: {0} {1:2}'.format(repe, c.codcir))
            for p, s in result.repre.items():
                if s > 0:
                    total[p] = total.get(p, 0) + s
        total = sorted(total.items(), key=lambda p: p[1], reverse=True)
        if show:
            print('{0}'.format(total)[1:-1])
        return total
