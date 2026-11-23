#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config_multicore.py — Configuración de Gem5 con jerarquía de caché.

Corrige el problema CRÍTICO P1 de la auditoría: la configuración anterior
conectaba la CPU directamente al membus -> mem_ctrls, sin L1/L2, por lo que
no existían fallos de caché reales (los "Misses" graficados eran fallos de
TLB de instrucciones).

Esta configuración usa el stdlib de Gem5 (v25.1) y añade:

    L1I (32 KiB) + L1D (32 KiB)  privadas por núcleo
    L2  (256 KiB)                compartida entre núcleos
    CPU O3CPU                    (fuera de orden, el modelo del proyecto)

Multihilo SE (parche sobre la stdlib):
    La stdlib de Gem5 (SimpleBoard/SimpleProcessor) está pensada para SE
    MONOHILO: cada núcleo arranca con numThreads=1. Un programa con pthreads
    necesita (NUM_HILOS workers + main) contextos de hilo en total.
    - Si (NUM_HILOS+1) <= nº de núcleos: NO hace falta SMT; clone() reparte
      los workers a los TCs idle de los demás núcleos (caso multicore nativo).
    - Si (NUM_HILOS+1) > nº de núcleos: hace falta SMT (numThreads>1) para
      tener TCs suficientes. Se activa con --num-threads.

    Activar SMT en esta stdlib exige 5 ajustes simultáneos (uno solo no
    basta): numThreads, vector isa, vector workload, system.multi_thread y
    conectar los puertos de interrupción de TODOS los hilos (la stdlib solo
    conecta interrupts[0]). Los cuatro primeros se hacen aquí; el quinto se
    parchea reemplazando BaseCPUCore.connect_interrupt.

Uso (ver run_gem5.sh):

    gem5.opt config_multicore.py \
        --cpu-cores=4 \
        --num-threads=2 \
        --cmd=./matrices_paralelo

Opciones:
    --cpu-cores N     Núcleos: 1, 2 o 4
    --num-threads T   Hilos hardware (SMT) por núcleo. Por defecto 1.
                      run_gem5.sh lo calcula como ceil((NUM_HILOS+1)/N).
    --cmd RUTA        Binario a ejecutar
    --args "..."      Argumentos del binario (separados por espacios)
    --l1d/--l1i/--l2  Tamaños de caché
    --mem 1GiB        Tamaño de memoria
    --clk 3GHz        Frecuencia del reloj
"""

import argparse
import os
import sys

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import (
    PrivateL1SharedL2CacheHierarchy,
)
from gem5.components.memory import SingleChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.isas import ISA
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires


# ---------------------------------------------------------------------------
# Parche: conectar las interrupciones de TODOS los hilos hardware.
#
# La stdlib (BaseCPUCore.connect_interrupt) solo conecta self.core.interrupts[0]
# al bus. Con numThreads>1 hay N controladores de interrupción y los demás quedan
# sin puerto -> panic "Int port not connected to anything" en init.
# Aquí se reemplaza por una versión que recorre los numThreads hilos. Con
# numThreads=1 es idéntica a la original (rango [0:1]), así que no afecta al
# caso mono-hilo.
# ---------------------------------------------------------------------------
def _connect_interrupt_all_threads(self, interrupt_requestor=None,
                                    interrupt_responce=None):
    self.core.createInterruptController()
    if self.get_isa().value == ISA.X86.value:
        nt = int(self.core.numThreads)
        for t in range(nt):
            if interrupt_requestor is not None:
                self.core.interrupts[t].pio = interrupt_requestor
                self.core.interrupts[t].int_responder = interrupt_requestor
            if interrupt_responce is not None:
                self.core.interrupts[t].int_requestor = interrupt_responce


BaseCPUCore.connect_interrupt = _connect_interrupt_all_threads


def parsear():
    p = argparse.ArgumentParser(
        description="Config multicore de Gem5 con cachés L1/L2 (stdlib)"
    )
    p.add_argument("--cpu-cores", type=int, default=1, choices=[1, 2, 4],
                   help="Número de núcleos (1, 2 o 4)")
    p.add_argument("--num-threads", type=int, default=1,
                   help="Hilos hardware (SMT) por núcleo. Por defecto 1. "
                        "Se necesita >1 cuando (NUM_HILOS+1) > nº de núcleos.")
    p.add_argument("--cmd", required=True,
                   help="Ruta del binario a ejecutar en modo SE")
    p.add_argument("--args", default="",
                   help="Argumentos del binario, separados por espacios")
    p.add_argument("--l1d", default="32KiB", help="Tamaño L1 datos")
    p.add_argument("--l1i", default="32KiB", help="Tamaño L1 instrucciones")
    p.add_argument("--l2", default="256KiB", help="Tamaño L2 compartida")
    p.add_argument("--mem", default="1GiB", help="Tamaño de memoria")
    p.add_argument("--clk", default="3GHz", help="Frecuencia del reloj")
    p.add_argument("--cpu-type", default="O3",
                   choices=["O3", "TIMING", "ATOMIC"],
                   help="Modelo de CPU")
    return p.parse_args()


def main():
    args = parsear()

    binario = os.path.abspath(args.cmd)
    if not os.path.isfile(binario):
        sys.exit("ERROR: no existe el binario: {0}".format(binario))
    if not os.access(binario, os.X_OK):
        sys.exit("ERROR: el binario no es ejecutable: {0}".format(binario))

    # Este build solo soporta X86.
    requires(isa_required=ISA.X86)

    # --- Cachés: L1 privada por núcleo + L2 compartida -------------------
    cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
        l1d_size=args.l1d,
        l1i_size=args.l1i,
        l2_size=args.l2,
        l1d_assoc=8,
        l1i_assoc=8,
        l2_assoc=16,
    )

    # --- Memoria ---------------------------------------------------------
    memory = SingleChannelDDR4_2400(size=args.mem)

    # --- Procesador: N núcleos O3 ---------------------------------------
    cpu_types = {
        "O3": CPUTypes.O3,
        "TIMING": CPUTypes.TIMING,
        "ATOMIC": CPUTypes.ATOMIC,
    }
    processor = SimpleProcessor(
        cpu_type=cpu_types[args.cpu_type],
        isa=ISA.X86,
        num_cores=args.cpu_cores,
    )

    # --- SMT: numThreads por núcleo -------------------------------------
    # La stdlib crea cada núcleo con numThreads=1 e invoca createThreads() (que
    # fija isa=[1] y decoder=[1]). Para tener T hilos hay que: subir numThreads,
    # vaciar isa y decoder, y volver a llamar a createThreads() (regenera T
    # isa/decoder). El proceso (workload) se replica tras set_se_binary_workload.
    if args.num_threads > 1:
        for core in processor.get_cores():
            sim = core.get_simobject()
            sim.numThreads = args.num_threads
            sim.isa = []
            sim.decoder = []
            sim.createThreads()

    # --- Board -----------------------------------------------------------
    board = SimpleBoard(
        clk_freq=args.clk,
        processor=processor,
        memory=memory,
        cache_hierarchy=cache_hierarchy,
    )

    # --- System multihilo (necesario si algún CPU tiene numThreads>1) ----
    # registerThreadContexts() exige system->multiThread. SimpleBoard hereda
    # de System, así que el flag vive en el propio board.
    if args.num_threads > 1:
        board.multi_thread = True

    # --- Cargar el binario en modo SE -----------------------------------
    argumentos = args.args.split() if args.args else []
    board.set_se_binary_workload(
        binary=BinaryResource(local_path=binario, architecture=ISA.X86),
        arguments=argumentos,
        exit_on_work_items=True,
    )

    # --- Replicar el proceso en cada contexto de hilo --------------------
    # set_se_binary_workload deja cpu.workload=[process] (1 entrada). Con
    # numThreads>1 Gem5 exige una entrada por hilo; todas comparten el mismo
    # Process (mismo espacio de direcciones). El hilo 0 arranca main; los
    # demás quedan como TC libre para que clone()/pthread_create los reutilice.
    if args.num_threads > 1:
        for core in processor.get_cores():
            sim = core.get_simobject()
            sim.workload = [sim.workload[0]] * args.num_threads

    print("Configuración: {0} núcleo(s) {1}, {2} hilo(s)/núcleo, L1I={3} "
          "L1D={4} L2={5}, mem={6}, clk={7}".format(
              args.cpu_cores, args.cpu_type, args.num_threads, args.l1i,
              args.l1d, args.l2, args.mem, args.clk))
    print("Binario: {0} {1}".format(binario, " ".join(argumentos)))
    print()

    sim = Simulator(board=board, full_system=False)
    sim.run()

    print()
    print("Simulación terminada @ tick {0}".format(sim.get_current_tick()))
    print("Causa de salida: {0}".format(sim.get_last_exit_event_cause()))


# Gem5 ejecuta los scripts de configuración con __name__ == "__m5_main__"
# (ver src/python/m5/main.py: scope = {"__name__": "__m5_main__"}).
# Se aceptan ambos nombres para poder probar el script con python3 normal.
if __name__ in ("__m5_main__", "__main__"):
    main()
