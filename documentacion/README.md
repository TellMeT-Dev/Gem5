# proyectoGem5 — Multiplicación de matrices multi-hilo en Gem5

Compara el rendimiento de una multiplicación de matrices **100×100** ejecutada de
forma **secuencial** y **paralela** (POSIX threads) sobre un procesador simulado
con **Gem5**, barriendo configuraciones de **1, 2 y 4 núcleos** combinados con
**1, 2 y 4 hilos**.

> Los `stats.txt` incluidos son salidas **reales de Gem5**
> (modelo **TimingSimpleCPU**, jerarquía **L1I/L1D 32 KiB + L2 256 KiB**),
> no datos sintéticos.
>
> **Configuraciones disponibles:** 8 de 10 posibles. Los configs 2c/4t y
> 4c/4t no se pueden simular con TimingSimpleCPU (limitación de gem5 con
> SMT multicore); están documentados como limitación conocida.

---

## Estructura del proyecto

```
proyectoGem5/
├── Makefile                        Compilación de los programas en C
├── run_gem5.sh                     Barrido automático núcleos × hilos en Gem5
├── config_multicore.py             Config de Gem5 CON jerarquía L1/L2
│
├── matrices_secuencial.c           Mult. secuencial (sin hilos)
├── matrices_paralelo.c             Mult. paralela con pthreads
│
├── extraer_stats.py                Lee los stats.txt → metricas.csv
├── Graficas.py                     Gráficas comparativas (lee del CSV)
├── EficienciaParalela.py           Eficiencia paralela (lee del CSV)
├── metricas.csv                    Generado por extraer_stats.py
│
├── stats_secuencial.txt            Stats Gem5 referencia secuencial
├── cpu1_1hilo.txt  cpu1_2hilo.txt  cpu1_4hilo.txt    1 núcleo  × 1/2/4 hilos
├── cpu2_1hilo.txt  cpu2_2hilo.txt                    2 núcleos × 1/2 hilos
├── cpu4_1hilo.txt  cpu4_2hilo.txt                    4 núcleos × 1/2 hilos
│
├── manuales/
│   ├── Secuencial.docx             Informe con capturas y gráficas
│   └── estadisticas.xlsx           Tabla resumen
│
├── documentacion/
│   ├── README.md                   Este archivo
│   └── AUDITORIA.md                Auditoría técnica previa (referencia)
│
└── *.png                           Gráficas generadas por los scripts
```

Los binarios (`matrices_secuencial`, `matrices_paralelo`) y `metricas.csv` no
se guardan en el repo: se regeneran con `make` y `python3 extraer_stats.py`.

---

## Requisitos

| Componente | Uso | Obligatorio |
|---|---|---|
| Linux + gcc | Compilar los `.c` | Sí |
| Python 3 | Extraer métricas | Sí |
| `matplotlib` | Generar gráficas | Para gráficas |
| Gem5 (v21+) | Re-simular experimentos | Solo para re-ejecutar |

Instalar dependencias de gráficas:

```bash
pip install matplotlib          # o: apt install python3-matplotlib
```

> **Nota:** `extraer_stats.py` solo usa la librería estándar de Python, corre
> sin `pandas` ni `matplotlib`.

---

## Instalación de Gem5

`config_multicore.py` usa la *stdlib* de **Gem5 v25.1** (clases `SimpleBoard`,
`PrivateL1SharedL2CacheHierarchy`, `Simulator`, `BinaryResource`...), así que
hace falta un `gem5.opt` compilado para la ISA **X86**. Pasos verificados en
este equipo (Ubuntu, Python 3.14, gcc 15, 16 núcleos).

> **Estado en este equipo:** ya está clonado en `/run/media/tellmedev/Externo/gem5`
> (rama `v25.1`) y compilado en `build/X86/gem5.opt`. Solo es necesario
> re-ejecutar el paso 4 para volver a simular.

### 1. Dependencias de compilación

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential scons python3-dev python3-pip python3-six python3-pydot \
  protobuf-compiler libprotobuf-dev libgoogle-perftools-dev libhdf5-dev \
  libpng-dev libboost-all-dev zlib1g-dev m4 libcapstone-dev libbfd-dev \
  libelf-dev pkg-config
```

### 2. Clonar Gem5 (rama v25.1)

```bash
cd /run/media/tellmedev/Externo
git clone -b v25.1 https://github.com/gem5/gem5.git
```

### 3. Compilar `gem5.opt` para X86

```bash
cd /run/media/tellmedev/Externo/gem5
scons build/X86/gem5.opt -j$(nproc)
```

El binario queda en `build/X86/gem5.opt` (~1 GB; al ser un build *opt* con
debug info tarda varios minutos). Verificar que corre:

```bash
./build/X86/gem5.opt   # imprime la cabecera "gem5 version 25.1.0.0"
```

### 4. Apuntar el script al binario

```bash
cd "/run/media/tellmedev/Externo/Universidad/VI_Semestre/Arquitectura de Computadores/proyectoGem5"
./run_gem5.sh /run/media/tellmedev/Externo/gem5/build/X86/gem5.opt
```

o, sin pasar el argumento, exportar la variable de entorno:

```bash
export GEM5_BIN=/run/media/tellmedev/Externo/gem5/build/X86/gem5.opt
./run_gem5.sh
```

> **Nota (Python 3.14 / PEP 668):** en este entorno `pip install` directo está
> bloqueado. Para `matplotlib` usar `sudo apt install python3-matplotlib` o
> `pip install --user --break-system-packages matplotlib`.

---

## Uso rápido

Todos los comandos se ejecutan **desde la raíz del proyecto** (no desde
`documentacion/`):

```bash
# 1. Compilar
make

# 2. Extraer métricas de los stats.txt reales
python3 extraer_stats.py

# 3. Generar gráficas
python3 Graficas.py
python3 EficienciaParalela.py
```

Las gráficas quedan como `.png` en la raíz del proyecto.

### Re-simular en Gem5

```bash
make
./run_gem5.sh /ruta/a/gem5.opt
```

El script recorre 1/2/4 núcleos × 1/2/4 hilos, guarda cada `stats.txt` y
vuelve a extraer métricas y gráficas automáticamente.

---

## Métricas que produce `metricas.csv`

| Columna | Descripción |
|---|---|
| `nucleos`, `hilos` | Configuración (0/0 = referencia secuencial) |
| `simticks`, `simseconds` | Tiempo simulado en Gem5 |
| `siminsts` | Instrucciones ejecutadas |
| `ciclos_total` | Suma de ciclos de todos los núcleos |
| `ipc_promedio` | IPC medio entre núcleos |
| `l1d_misses` | Fallos de caché L1 de datos (suma de todos los núcleos) |
| `l1i_misses` | Fallos de caché L1 de instrucciones (suma de todos los núcleos) |
| `l2_misses` | Fallos de caché L2 compartida |
| `cache_misses_total` | Suma de L1D + L1I + L2 |
| `tlb_misses_total` | Fallos de TLB (ITB + DTB) — distintos de los de caché |
| `cache` | Si la config tiene jerarquía de caché (`si`/`no`) |
| `branchestotal`, `loads`, `stores`, `fp_insts` | Estadísticas del pipeline |

**Speedup y eficiencia** se calculan desde el CSV:

```
speedup interno  = simTicks(1_hilo_misma_CPU) / simTicks(config)
speedup_vs_seq   = simTicks(secuencial)        / simTicks(config)
eficiencia       = speedup / N_hilos
```

---

## Limitaciones conocidas (ver `documentacion/AUDITORIA.md`)

Estos puntos se **corrigieron** re-simulando con `run_gem5.sh` sobre el Gem5
v25.1 ya instalado:

- **P1 — Cachés reales.** `config_multicore.py` añade L1I/L1D/L2 (privadas +
  compartida), y los `stats.txt` regenerados contienen fallos de caché reales
  extraídos por `extraer_stats.py` (columnas `l1d_misses`, `l1i_misses`,
  `l2_misses`, `cache_misses_total`). La gráfica `05_cache_misses.png` muestra
  los fallos por configuración.
- **Multihilo SE en Gem5 v25.1 (resuelto).** La stdlib `SimpleBoard`/
  `SimpleProcessor` arranca cada núcleo con `numThreads=1`; un programa con
  pthreads necesita (NUM_HILOS+1) contextos de hilo. Si eso cabe en los N
  núcleos (sin SMT), `clone()` reparte los workers a los TCs libres de los
  demás núcleos. Si no cabe, hace falta SMT (`numThreads>1`). Activar SMT en
  esta stdlib exige 5 ajustes simultáneos — `numThreads`, vector `isa`, vector
  `workload`, `system.multi_thread` y conectar las interrupciones de **todos**
  los hilos (la stdlib solo conecta `interrupts[0]`); los 4 primeros se hacen
  en `config_multicore.py` y el quinto parcheando
  `BaseCPUCore.connect_interrupt`. `run_gem5.sh` calcula
  `--num-threads=ceil((NUM_HILOS+1)/N)` por configuración.
- **P2/P3 — Workloads comparables.** `run_gem5.sh` fija `TAM=100` y semilla
  idéntica (sin `srand` → semilla 1) en todas las configuraciones, así
  `simInsts` es comparable (~6.2 M en todas); antes variaba entre ~1.9 M y
  ~63 M. La gráfica `07_siminsts.png` ahora muestra esa consistencia.
- **P7/P8/P9 — Decisiones mantenidas a propósito en el código C** (se conservan
  según lo acordado): `TAM` y `NUM_HILOS` siguen como `#define`, no hay
  checksum de verificación, y se usa `clock()`.

### Correcciones ya aplicadas

- **P5** — Los datos ya no están hardcodeados: `extraer_stats.py` lee los
  `stats.txt` y los scripts trabajan desde `metricas.csv`.
- **P6** — Normalización de speedup de CPU1 corregida en
  `EficienciaParalela.py` (antes usaba base desplazada T2/T1, T4/T2).
- **P10** — Añadidos `Makefile` y `run_gem5.sh`.
- **P11** — Añadido este `README.md`.
- **P12** — Se extraen estadísticas del pipeline O3 (`numBranches`, loads,
  stores) y se grafican.
- **P14** — Nueva gráfica `02_speedup_vs_secuencial.png` que normaliza contra
  la referencia secuencial.
