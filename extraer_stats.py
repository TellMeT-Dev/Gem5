#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extractor automático de estadísticas de Gem5.

Lee los archivos de estadísticas de esta carpeta y genera ``metricas.csv``
con las métricas de cada configuración.

Solo usa la librería estándar de Python (sin pandas ni matplotlib).

Diseño robusto: en vez de buscar rutas exactas como ``system.cpu.numCycles``
(según la config, el stdlib de Gem5 nombra los objetos distinto), se buscan
**sufijos inequívocos** al final de la clave:

    ...numCycles          -> ciclos por núcleo (se suman)
    ...ipc                -> IPC por núcleo (se promedia)
    ...mmu.itb.exMisses   -> fallos de TLB de instrucciones
    ...mmu.dtb.*Misses    -> fallos de TLB de datos
    ...l1dcaches*.demandMisses::total -> fallos de caché L1 de datos
    ...l1icaches*.demandMisses::total -> fallos de caché L1 de instrucciones
    ...l2cache.demandMisses::total     -> fallos de caché L2 (compartida)
    ...executeStats0.numBranches -> ramas (pipeline O3)
    ...commitStats0.numLoadInsts -> loads (pipeline O3)

La jerarquia de caché (L1I/L1D privadas + L2 compartida) la pone
``config_multicore.py``. El nombre de los objetos L1 depende del numero de
nucleos: ``l1dcaches`` (1 nucleo, sin indice) o ``l1dcaches0``, ``l1dcaches1``
(2+ nucleos). Por eso el patron usa ``\\d*`` (cero o mas digitos).

Las claves globales de Gem5 (``simTicks``, ``simInsts``...) no llevan punto
y se toman tal cual.

Uso:
    python3 extraer_stats.py
"""

import csv
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_SALIDA = os.path.join(BASE_DIR, "metricas.csv")

# (config_nucleos, hilos, archivo)
CONFIGURACIONES = [
    (0, 0, "stats_secuencial.txt"),  # 0 = referencia secuencial
    (1, 1, "cpu1_1hilo.txt"),
    (1, 2, "cpu1_2hilo.txt"),
    (1, 4, "cpu1_4hilo.txt"),
    (2, 1, "cpu2_1hilo.txt"),
    (2, 2, "cpu2_2hilo.txt"),
    (2, 4, "cpu2_4hilo.txt"),
    (4, 1, "cpu4_1hilo.txt"),
    (4, 2, "cpu4_2hilo.txt"),
    (4, 4, "cpu4_4hilo.txt"),
]

# Claves globales (sin jerarquía, siempre al inicio de la línea)
CLAVES_GLOBALES = {
    "simTicks": "simticks",
    "simInsts": "siminsts",
    "simSeconds": "simseconds",
    "hostSeconds": "hostseconds",
}

# Sufijos inequívocos -> dónde acumular
#   (patrón del final de la clave, campo de destino, es suma o promedio)
#
# NOTA: se excluye "Stats0" del final para no confundir el IPC de nivel núcleo
# (board.processor.cores.core.ipc) con el de nivel hilo
# (board.processor.cores.core.commitStats0.ipc).
SUFJOS = [
    (re.compile(r"(?<!Stats0)\.numCycles$"),          "ciclos_total", "suma"),
    (re.compile(r"(?<!Stats0)\.ipc$"),                "ipc_suma",     "prom"),
    (re.compile(r"\.mmu\.itb\.exMisses$"),            "itb_misses",   "suma"),
    (re.compile(r"\.mmu\.dtb\.rdMisses$"),            "dtb_rd",       "suma"),
    (re.compile(r"\.mmu\.dtb\.wrMisses$"),            "dtb_wr",       "suma"),
    (re.compile(r"\.executeStats0\.numBranches$"),    "branches",     "suma"),
    (re.compile(r"\.fetchStats0\.numBranches$"),      "fetch_br",     "suma"),
    (re.compile(r"\.commitStats0\.numLoadInsts$"),    "loads",        "suma"),
    (re.compile(r"\.commitStats0\.numStoreInsts$"),   "stores",       "suma"),
    (re.compile(r"\.commitStats0\.numFpInsts$"),      "fp_insts",     "suma"),
    # ---- Fallos de caché (L1D, L1I, L2) ----
    # l1dcaches (1 nucleo) o l1dcaches0, l1dcaches1 (2+ nucleos): \d* cubre ambos.
    (re.compile(r"\.l1dcaches\d*\.demandMisses::total$"), "l1d_misses", "suma"),
    (re.compile(r"\.l1icaches\d*\.demandMisses::total$"), "l1i_misses", "suma"),
    (re.compile(r"\.l2cache\.demandMisses::total$"),      "l2_misses",  "suma"),
]

# Instrucciones por núcleo/hilo (para detectar el reparto de trabajo)
RE_INSTS_NUCLEO = re.compile(r"\.thread[_\.]?[0-9]+\.numInsts$")

# Jerarquía de caché presente (para detectar si la config la tiene).
# Cubre nombres del stdlib (board.cache_hierarchy.l1dcaches...) y rutas
# clásicas (system.l1d...).
RE_CACHE = re.compile(
    r"l1[di]cache|l2cache|\.l1[di][._]|\.l2[._]|\.dcache\.|\.icache\.",
    re.IGNORECASE,
)

NUM_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")


def _a_numero(texto):
    """Convierte un valor de stat a float; devuelve None si no es numerico."""
    if texto is None or not NUM_RE.match(texto):
        return None
    return float(texto)


def parsear_stats(ruta):
    """Devuelve un dict con las metricas extraidas de un archivo stats.txt."""
    m = {
        "simticks": None,
        "siminsts": None,
        "simseconds": None,
        "hostseconds": None,
        "ciclos_total": 0.0,
        "ipc_suma": 0.0,
        "ipc_nucleos": 0,
        "itb_misses": 0.0,
        "dtb_rd": 0.0,
        "dtb_wr": 0.0,
        "branches": 0.0,
        "fetch_br": 0.0,
        "loads": 0.0,
        "stores": 0.0,
        "fp_insts": 0.0,
        "l1d_misses": 0.0,
        "l1i_misses": 0.0,
        "l2_misses": 0.0,
        "insts_nucleo": 0.0,
        "num_nucleos": 0,
        "con_cache": False,
    }

    nucleos_vistos = set()

    with open(ruta, "r", errors="replace") as fh:
        for linea in fh:
            linea = linea.rstrip("\n")
            if not linea or linea[0] in "-#":
                continue

            # Separar clave y valor: la clave es el primer campo no numérico
            partes = linea.split()
            if len(partes) < 2:
                continue
            clave, valor_txt = partes[0], partes[1]

            # ---- Claves globales (simTicks, simInsts, ...) ----
            if clave in CLAVES_GLOBALES:
                val = _a_numero(valor_txt)
                if val is not None:
                    m[CLAVES_GLOBALES[clave]] = val
                continue

            # Solo las claves con jerarquía nos interesan a partir de aquí
            if "." not in clave:
                continue

            # ---- Instrucciones por núcleo (thread_0.numInsts) ----
            if RE_INSTS_NUCLEO.search(clave):
                val = _a_numero(valor_txt)
                if val is not None:
                    m["insts_nucleo"] += val
                    # El prefijo antes de .thread_X.numInsts identifica al núcleo
                    nucleo = clave.split(".thread")[0]
                    nucleos_vistos.add(nucleo)
                continue

            # ---- Cache presente? ----
            if RE_CACHE.search(clave):
                m["con_cache"] = True

            # ---- Sufijos acumulables ----
            for patron, campo, modo in SUFJOS:
                if patron.search(clave):
                    val = _a_numero(valor_txt)
                    if val is None:
                        break
                    if modo == "suma":
                        m[campo] += val
                    else:  # promedio
                        m[campo] += val
                        m["ipc_nucleos"] += 1
                        nucleos_vistos.add(clave.rsplit(".", 1)[0])
                    break

    m["num_nucleos"] = len(nucleos_vistos) if nucleos_vistos else 1
    return m


def main():
    filas = []
    faltantes = []

    for nucleos, hilos, archivo in CONFIGURACIONES:
        ruta = os.path.join(BASE_DIR, archivo)
        if not os.path.isfile(ruta):
            faltantes.append(archivo)
            continue

        m = parsear_stats(ruta)

        ipc = (m["ipc_suma"] / m["ipc_nucleos"]) if m["ipc_nucleos"] else None
        dtb_total = m["dtb_rd"] + m["dtb_wr"]

        filas.append({
            "nucleos": nucleos,
            "hilos": hilos,
            "archivo": archivo,
            "simticks": m["simticks"],
            "siminsts": m["siminsts"],
            "simseconds": m["simseconds"],
            "hostseconds": m["hostseconds"],
            "ciclos_total": m["ciclos_total"] or None,
            "insts_por_nucleo": m["insts_nucleo"] or None,
            "ipc_promedio": round(ipc, 6) if ipc is not None else None,
            "itb_misses": m["itb_misses"],
            "dtb_misses": dtb_total,
            "tlb_misses_total": m["itb_misses"] + dtb_total,
            "cache": "si" if m["con_cache"] else "no",
            "l1d_misses": m["l1d_misses"] or None,
            "l1i_misses": m["l1i_misses"] or None,
            "l2_misses": m["l2_misses"] or None,
            "cache_misses_total": (m["l1d_misses"] + m["l1i_misses"]
                                   + m["l2_misses"]) or None,
            "branchestotal": m["branches"] or None,
            "loads": m["loads"] or None,
            "stores": m["stores"] or None,
            "fp_insts": m["fp_insts"] or None,
        })

    if faltantes:
        print("AVISO: no se encontraron los siguientes archivos:",
              file=sys.stderr)
        for archivo in faltantes:
            print("  - " + archivo, file=sys.stderr)

    if not filas:
        print("ERROR: no se pudo leer ningun archivo de estadisticas",
              file=sys.stderr)
        return 1

    campos = list(filas[0].keys())
    with open(CSV_SALIDA, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)

    # ---- Speedup y eficiencia (base = secuencial, ver AUDITORIA P14) ----
    base = next((f for f in filas if f["nucleos"] == 0), None)
    if base and base["simticks"]:
        t_seq = base["simticks"]
        print()
        print("Speedup con base secuencial (simTicks_seq / simTicks_N):")
        print("  {0:<8} {1:<6} {2:>14} {3:>10} {4:>9}".format(
            "nucleos", "hilos", "simTicks", "speedup", "eficiencia"))
        for f in filas:
            if f["nucleos"] == 0 or not f["simticks"]:
                continue
            sp = t_seq / f["simticks"]
            ef = sp / f["hilos"] if f["hilos"] else None
            print("  {0:<8} {1:<6} {2:>14} {3:>10.3f} {4:>9.3f}".format(
                f["nucleos"], f["hilos"], int(f["simticks"]), sp,
                ef if ef is not None else float("nan")))

    # ---- Speedup interno por CPU (base = 1 hilo de esa CPU) -------------
    print()
    print("Speedup interno (base = 1 hilo de cada CPU):")
    print("  {0:<8} {1:<6} {2:>10} {3:>9}".format(
        "nucleos", "hilos", "speedup", "eficiencia"))
    for n in (1, 2, 4):
        fila_base = next((f for f in filas
                          if f["nucleos"] == n and f["hilos"] == 1), None)
        if not fila_base or not fila_base["simticks"]:
            continue
        b = fila_base["simticks"]
        for h in (1, 2, 4):
            fila = next((f for f in filas
                         if f["nucleos"] == n and f["hilos"] == h), None)
            if not fila or not fila["simticks"]:
                continue
            sp = b / fila["simticks"]
            print("  {0:<8} {1:<6} {2:>10.3f} {3:>9.3f}".format(
                n, h, sp, sp / h))

    # ---- Aviso si no hay caché ------------------------------------------
    if filas and all(f["cache"] == "no" for f in filas):
        print()
        print("AVISO: ningun stats tiene jerarquia de cache.")
        print("       Los fallos de cache (L1/L2) seran 0; solo hay fallos de TLB.")

    print()
    print("CSV generado: " + CSV_SALIDA)
    print("Filas: {0}".format(len(filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
