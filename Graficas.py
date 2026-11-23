#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Graficas comparativas del experimento multi-hilo en Gem5.

Lee las metricas de ``metricas.csv`` (generado por ``extraer_stats.py``) y
produce las graficas PNG en esta misma carpeta.

Ya no hay valores hardcodeados: todo sale de los ``stats.txt`` reales.

Uso:
    python3 extraer_stats.py        # primero genera el CSV
    python3 Graficas.py

Dependencias: matplotlib (unicamente).
"""

import csv
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")  # sin display: guardar a archivo
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit(
        "ERROR: falta 'matplotlib'.\n"
        "  Instalar con:  pip install matplotlib   (o apt install python3-matplotlib)"
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_RUTA = os.path.join(BASE_DIR, "metricas.csv")
SALIDA_DIR = BASE_DIR

HILOS_ORDEN = [1, 2, 4]


def cargar():
    """Devuelve las filas del CSV como dicts con valores numericos."""
    if not os.path.isfile(CSV_RUTA):
        sys.exit(
            "ERROR: no existe {0}\n"
            "  Ejecuta antes:  python3 extraer_stats.py".format(CSV_RUTA)
        )

    filas = []
    with open(CSV_RUTA, newline="") as fh:
        for fila in csv.DictReader(fh):
            convertida = {}
            for k, v in fila.items():
                if v in (None, ""):
                    convertida[k] = None
                else:
                    try:
                        convertida[k] = float(v)
                    except ValueError:
                        convertida[k] = v
            filas.append(convertida)
    return filas


def serie(filas, campo, nucleos):
    """Devuelve [valor para hilo 1, hilo 2, hilo 4] de una CPU concreta."""
    salida = []
    for h in HILOS_ORDEN:
        match = [f for f in filas
                 if f["nucleos"] == nucleos and f["hilos"] == h]
        salida.append(match[0].get(campo) if match else None)
    return salida


def graficar(x, series, titulo, ylabel, nombre, escala_log=False):
    """Dibuja una serie por CPU y guarda la figura."""
    plt.figure(figsize=(11, 6))

    estilos = {
        1: ("CPU 1", "o", "-", "tab:blue"),
        2: ("CPU 2", "s", "--", "tab:green"),
        4: ("CPU 4", "^", ":", "tab:purple"),
    }

    for nucleos, (etiqueta, marker, linestyle, color) in estilos.items():
        y = series.get(nucleos)
        if y is None:
            continue
        plt.plot(x, y, marker=marker, linewidth=2.5, linestyle=linestyle,
                 color=color, label=etiqueta)

    plt.title(titulo, fontsize=15)
    plt.xlabel("Número de hilos", fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.xticks(x)
    if escala_log:
        plt.yscale("log")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    ruta = os.path.join(SALIDA_DIR, nombre)
    plt.savefig(ruta, dpi=150)
    plt.close()
    print("  grafica -> " + ruta)


def main():
    filas = cargar()
    os.makedirs(SALIDA_DIR, exist_ok=True)

    # Referencia secuencial (base de speedup, ver AUDITORIA P14)
    seq = next((f for f in filas if f["nucleos"] == 0), None)

    # ---- 1. Speedup interno (base = 1 hilo de cada CPU) -------------------
    speedup_int = {}
    for n in (1, 2, 4):
        base = serie(filas, "simticks", n)[0]
        if base:
            speedup_int[n] = [base / t if t else None
                              for t in serie(filas, "simticks", n)]

    print("Generando graficas...")
    graficar(HILOS_ORDEN, speedup_int,
             "Speedup vs Número de Hilos (base: 1 hilo por CPU)",
             "Speedup", "01_speedup.png")

    # ---- 2. Speedup vs referencia secuencial (AUDITORIA P14) --------------
    speedup_seq = {}
    if seq and seq.get("simticks"):
        t_seq = seq["simticks"]
        for n in (1, 2, 4):
            ticks = serie(filas, "simticks", n)
            speedup_seq[n] = [t_seq / t if t else None for t in ticks]

        graficar(HILOS_ORDEN, speedup_seq,
                 "Speedup vs Secuencial de Referencia",
                 "Speedup (base secuencial)", "02_speedup_vs_secuencial.png")

    # ---- 3. Eficiencia paralela (speedup interno / hilos) -----------------
    eficiencia = {}
    for n, vals in speedup_int.items():
        eficiencia[n] = [v / h if v is not None else None
                         for v, h in zip(vals, HILOS_ORDEN)]

    plt.figure(figsize=(11, 6))
    colores = {1: "tab:blue", 2: "tab:green", 4: "tab:purple"}
    for n, vals in eficiencia.items():
        plt.plot(HILOS_ORDEN, vals, marker="o", markersize=8,
                 linewidth=2.5, color=colores[n], label="CPU {0}".format(n))
        for x, y in zip(HILOS_ORDEN, vals):
            if y is not None:
                plt.text(x, y + 0.05, "{0:.2f}".format(y),
                         ha="center", fontsize=9)

    plt.axhline(y=1, linestyle="--", color="red", linewidth=2,
                label="Eficiencia ideal (1.0)")
    plt.title("Análisis Detallado de Eficiencia Paralela", fontsize=15)
    plt.xlabel("Número de hilos", fontsize=12)
    plt.ylabel("Eficiencia paralela (Speedup / hilos)", fontsize=12)
    plt.xticks(HILOS_ORDEN)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    ruta_ef = os.path.join(SALIDA_DIR, "03_eficiencia.png")
    plt.savefig(ruta_ef, dpi=150)
    plt.close()
    print("  grafica -> " + ruta_ef)

    # ---- 4. IPC promedio ---------------------------------------------------
    ipc = {n: serie(filas, "ipc_promedio", n) for n in (1, 2, 4)}
    graficar(HILOS_ORDEN, ipc,
             "IPC vs Número de Hilos", "IPC", "04_ipc.png")

    # ---- 5. Fallos de caché (L1D + L1I + L2) ------------------------------
    cache = {n: serie(filas, "cache_misses_total", n) for n in (1, 2, 4)}
    graficar(HILOS_ORDEN, cache,
             "Fallos de Caché vs Número de Hilos (L1D + L1I + L2)",
             "Fallos de caché (Count)", "05_cache_misses.png")

    # ---- 6. Tiempo simulado ----------------------------------------------
    ticks = {n: serie(filas, "simticks", n) for n in (1, 2, 4)}
    graficar(HILOS_ORDEN, ticks,
             "Tiempo de Ejecución vs Hilos", "simTicks (log)", "06_simticks.png",
             escala_log=True)

    # ---- 7. Instrucciones ejecutadas (expone P2/P3) -----------------------
    insts = {n: serie(filas, "siminsts", n) for n in (1, 2, 4)}
    graficar(HILOS_ORDEN, insts,
             "Instrucciones Ejecutadas vs Hilos (debería ser constante)",
             "simInsts (log)", "07_siminsts.png", escala_log=True)

    # ---- 8. Estadisticas de pipeline O3 (AUDITORIA P12) -------------------
    ramas = {n: serie(filas, "branchestotal", n) for n in (1, 2, 4)}
    graficar(HILOS_ORDEN, ramas,
             "Ramas Ejecutadas (pipeline O3) vs Hilos",
             "numBranches", "08_branches.png")

    print()
    print("Listo. Graficas en: " + BASE_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
