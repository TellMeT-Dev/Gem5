#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grafica de eficiencia paralela.

Lee ``metricas.csv`` (generado por ``extraer_stats.py``).

Correccion aplicada (AUDITORIA P6): la version anterior normalizaba mal CPU1
usando una base desplazada (T2/T1, T4/T2, 1) en lugar de (1, T1/T2, T1/T4),
lo que daba eficiencias ~1.0 espurias. Ahora el speedup se calcula siempre
como  base / tiempo, con base = tiempo de 1 hilo de la MISMA CPU.

Uso:
    python3 extraer_stats.py
    python3 EficienciaParalela.py

Dependencias: matplotlib (unicamente).
"""

import csv
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
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
    if not os.path.isfile(CSV_RUTA):
        sys.exit(
            "ERROR: no existe {0}\n"
            "  Ejecuta antes:  python3 extraer_stats.py".format(CSV_RUTA)
        )
    filas = []
    with open(CSV_RUTA, newline="") as fh:
        for fila in csv.DictReader(fh):
            conv = {}
            for k, v in fila.items():
                try:
                    conv[k] = float(v)
                except (TypeError, ValueError):
                    conv[k] = v
            filas.append(conv)
    return filas


def ticks_de(filas, nucleos, hilos):
    for f in filas:
        if f["nucleos"] == nucleos and f["hilos"] == hilos:
            return f.get("simticks")
    return None


def main():
    filas = cargar()
    os.makedirs(SALIDA_DIR, exist_ok=True)

    colores = {1: "tab:blue", 2: "tab:green", 4: "tab:purple"}

    plt.figure(figsize=(11, 6))

    print("Eficiencia paralela (base = 1 hilo de cada CPU):")
    print("  {0:<8} {1:<6} {2:>12} {3:>10} {4:>10}".format(
        "nucleos", "hilos", "simTicks", "speedup", "eficiencia"))

    for nucleos in (1, 2, 4):
        base = ticks_de(filas, nucleos, 1)
        if not base:
            continue

        hilos, speedups, eficiencias = [], [], []
        for h in HILOS_ORDEN:
            t = ticks_de(filas, nucleos, h)
            if not t:
                continue
            sp = base / t              # base / tiempo  -> 1 en 1 hilo
            ef = sp / h
            hilos.append(h)
            speedups.append(sp)
            eficiencias.append(ef)
            print("  {0:<8} {1:<6} {2:>12} {3:>10.4f} {4:>10.4f}".format(
                nucleos, h, int(t), sp, ef))

        plt.plot(hilos, eficiencias, marker="o", markersize=8,
                 linewidth=2.5, color=colores[nucleos],
                 label="CPU {0}".format(nucleos))

        for x, y in zip(hilos, eficiencias):
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

    ruta = os.path.join(SALIDA_DIR, "03_eficiencia.png")
    plt.savefig(ruta, dpi=150)
    plt.close()

    print()
    print("Grafica guardada: " + ruta)
    print("(Corregido P6: CPU1 ya no usa normalizacion desplazada.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
