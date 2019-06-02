#!/usr/bin/env python3

import csv
import os
import textwrap
from io import BytesIO, TextIOWrapper
from urllib.parse import urljoin
from urllib.request import urlopen
from zipfile import ZipFile

import bs4
import pandas as pd
import requests
import yaml
from bunch import Bunch
from unidecode import unidecode

me = os.path.realpath(__file__)
dr = os.path.dirname(me)

root_url = "http://www.resultadoseleccionesparlamentoandalucia2018.es/Mesas"
root_json = "http://www.resultadoseleccionesparlamentoandalucia2018.es/01json/ini01v.json"
resu_json = "http://www.resultadoseleccionesparlamentoandalucia2018.es/01json/AU/DAU0100099999.json"


def get_soup(url):
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.content, "lxml")
    for a in soup.findAll("a"):
        href = a.attrs.get("href", "#")
        if not href.startswith("#"):
            a.attrs["href"] = urljoin(url, href)
    return soup


def get_json(url):
    r = requests.get(url)
    js = r.json()
    if isinstance(js, dict):
        return Bunch(**js)
    if isinstance(js, list) and len(js) > 0 and isinstance(js[0], dict):
        return [Bunch(**j) for j in js]
    return js


def get_municipios():
    js = get_json(root_json)
    for i in js.mesas:
        url = urljoin(root_json, i["link"])
        yield (i["texto"], url)


def linkUrl(url):
    text = url.split("://", 1)[-1]
    if text.startswith("www."):
        text = text[4:]
    if text.endswith("/"):
        text = text[:-1]
    return "[%s](%s)" % (text, url)


def read_csv_zip(url, sufix):
    resp = urlopen(url)
    zip = BytesIO(resp.read())
    with ZipFile(zip) as zipfile:
        for file in zipfile.namelist():
            if file.endswith(sufix):
                with zipfile.open(file, "r") as csvfile:
                    text = TextIOWrapper(
                        csvfile, encoding='ISO-8859-1', newline='\r\n')
                    data = csv.DictReader(text, delimiter=";")
                    for d in data:
                        if d.get("Codcir", "Total") != "Total":
                            new_d = {}
                            for k, v in d.items():
                                if not k or v is None:
                                    continue
                                _v = v.replace(".", "")
                                if _v.isdigit():
                                    v = int(_v)
                                new_d[k] = v
                            yield new_d


def parse_key(_k):
    _k = unidecode(_k)
    k = _k.lower()
    if k in ("certif. alta", "censo", "municipio", "mesa", "codmun", "codcir", "certif. correc."):
        return None
    if k in ("censo total", "votos totales"):
        return k.split()[0]
    if k in ("votos nulos", "votos blancos", "votos electores", "votos interventores", "votos validos", "votos candidaturas"):
        return k.split()[-1]
    if k in ("codcir", "codmun", "municipio", "abstencion"):
        return k
    return _k


def get_data(sufix, *urls):
    data = []
    for url in urls:
        for d in read_csv_zip(url, sufix=sufix):
            data.append(d)
    return data


def get_and_save(name, *urls):
    sufix = "_"+name.title()+".csv"
    data = get_data(sufix, *urls)
    save(name, data)
    return data


def save_aggregate(mesas=None, municipios=None):
    if mesas is None:
        mesas = load("mesas")
    if municipios is None:
        municipios = load("municipios")
    cir_data = {d["codcir"]: d for d in get_info()}
    mesa_keys = set()
    for d in mesas:
        cir = d["Codcir"]
        dt = cir_data[cir]
        for k, v in d.items():
            mesa_keys.add(k)
            k = parse_key(k)
            if k:
                dt[k] = dt.get(k, 0) + v
        cir_data[cir] = dt
    for d in municipios:
        cir = d["Codcir"]
        dt = cir_data[cir]
        for k, v in d.items():
            if k in mesa_keys:
                continue
            k = parse_key(k)
            if k:
                dt[k] = dt.get(k, 0) + v
        cir_data[cir] = dt
    circunscripciones = []
    for dt in cir_data.values():
        c = {"partidos": {}}
        for k, v in dt.items():
            if k[0].upper() == k[0]:
                c["partidos"][k] = v
            else:
                c[k] = v
        circunscripciones.append(c)
    save("circunscripciones", circunscripciones)
    return cir_data


def save(name, data):
    if isinstance(data, dict):
        data = list(data.values())
    if len(data) > 0 and "codcir" in data[0]:
        data = sorted(data, key=lambda d: d["codcir"])
    with open(dr+"/data/"+name+".yml", "w") as f:
        yaml.safe_dump_all(data, f, default_flow_style=False,
                           allow_unicode=True, default_style=None)


def load(name, to_bunch=False):
    file = dr+"/data/"+name+".yml"
    if not os.path.isfile(file):
        return []
    with open(file, "r") as f:
        r = yaml.safe_load_all(f)
        if to_bunch:
            return [Bunch(**i) for i in r]
        return list(r)


def get_info():
    info = load("info")
    if len(info) == 0:
        js = get_json(resu_json)
        diputados = {d["NOMBRE"]: int(d["CANELE"]) for d in js["ambs"]}
        for text, link in get_municipios():
            d = next(read_csv_zip(link, sufix="_Municipios.csv"))
            codcir = d["Codcir"]
            info.append({
                "codcir": codcir,
                "url": link,
                "nombre": text,
                "diputados": diputados[text]
            })
        save("info", info)
    return info


def main():
    urls = []
    with open(dr+"/README.md", "w") as f:
        f.write(textwrap.dedent('''
            # Paralamento de Andalucía 2018

            **Fuente**: %s
            ''').lstrip() % linkUrl(root_url))
        for c in get_info():
            f.write("\n* [%s](%s)" % (c["nombre"], c["url"]))
            urls.append(c["url"])
    mesas = get_and_save("mesas", *urls)
    municipios = get_and_save("municipios", *urls)
    save_aggregate(mesas, municipios)


if __name__ == "__main__":
    pass
