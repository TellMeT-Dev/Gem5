# AUDITORÍA TÉCNICA — SIMULACIÓN DE RENDIMIENTO MULTIHILO EN GEM5

> Auditoría realizada sobre el proyecto `proyectoGem5`. Inspección sin modificar archivos.
> Cumplimiento estimado sobre requisitos verificables: **70.4 %** (27 cumplidos, 15 parciales, 7 no cumplidos, 2 no verificables).

---

## 6.1. Resumen ejecutivo

**Qué hace actualmente el proyecto.** Compara el rendimiento de la multiplicación de matrices (100×100) ejecutada de forma secuencial y paralela (POSIX threads) sobre un procesador simulado en Gem5, barriendo configuraciones de 1, 2 y 4 núcleos combinadas con 1, 2 y 4 hilos. Existen dos programas en C (`matrices_secuencial.c`, `matrices_paralelo.c`), un conjunto de **estadísticas reales de Gem5** (10 archivos `stats.txt` con `Begin/End Simulation Statistics`, `simTicks`, `numCycles`, `cpi`, etc.), una hoja de cálculo manual (`estadisticas.xlsx`) y dos scripts de graficación (`Graficas.py`, `EficienciaParalela.py`).

**Cerca del objetivo.** El núcleo experimental sí se ejecutó dentro de Gem5 (verificable) y se cubren las 9 celdas de la matriz núcleos×hilos más una referencia secuencial. El proyecto está razonablemente cerca del objetivo en lo que respecta a *ejecutar* el experimento. Sin embargo, está **lejos en los aspectos de rigor metodológico, reproducibilidad y automatización**: faltan todos los artefactos de configuración/compilación/ejecución, los workloads no son comparables entre configuraciones, no hay jerarquía de caché (por lo que no existen fallos de caché reales), las gráficas usan datos *hardcodeados* (no extraídos automáticamente) y hay inconsistencias de datos entre la hoja, los dos scripts de graficación y los `stats.txt`.

**Principales fortalezas.**

- Los `stats.txt` son salidas genuinas de Gem5 (formato, `hostSeconds`, `simFreq`, `End Simulation Statistics`), no inventadas.
- El modelo de CPU empleado es **O3CPU** (evidencia: `commitStats0`, `executeStats0`, `fetchStats0`, `numBranches` por etapa, `issuedInstType` por unidad funcional), el modelo detallado out-of-order apropiado para este estudio.
- Las 3 configuraciones de núcleos son reales: `cpu_1`→1 `numCycles`, `cpu_2`→2, `cpu_4`→4 (líneas `system.cpuN.numCycles` confirmadas).
- La partición por filas del programa paralelo es correcta y libre de carreras (cada hilo escribe filas disjuntas; `A`/`B` son solo lectura); `pthread_create`/`pthread_join` bien usados.
- Se calculan speedup y eficiencia y se generan las gráficas solicitadas.

**Principales deficiencias.**

- **Sin cachés**: las CPUs conectan directamente al `membus`→`mem_ctrls`; no hay objetos L1/L2. El requisito "fallos de caché" es **imposible** de satisfacer con esta configuración; los valores "Misses" graficados (232/250/177/71) son en realidad **fallos de TLB de instrucciones** (`mmu.itb.exMisses`), mal etiquetados.
- **Workloads no comparables**: `cpu_1` ejecutó ~1.9 M instrucciones mientras `cpu_2`/`cpu_4` ejecutaron ~63 M (≈33× más). Además, dentro de `cpu_2`/`cpu_4` las instrucciones totales *disminuyen* al subir hilos (63 M→32 M→17 M en `cpu_2`), violando el supuesto de trabajo constante que valida cualquier speedup.
- **Sin automatización**: los scripts Python tienen los valores escritos a mano (no leen `stats.txt`); la hoja muestra que se usó `Select-String` manual. `Graficas.py` admite en comentario *"tomamos el más estable (último o base corregida)"*, es decir, corrección manual.
- **Inconsistencia de datos**: los valores de speedup de CPU1 en `EficienciaParalela.py` (1.000626834, 1.001244372, 1.0) **no coinciden** con `Graficas.py` (1, 0.999373559, 1) ni con la hoja; resultan de una normalización desplazada (T2/T1, T4/T2, 1) en lugar de la correcta (1, T1/T2, T1/T4).
- **Sin verificación** de que el resultado paralelo coincide con el secuencial, y `NUM_HILOS` está como `#define` (requiere recompilar para cambiar hilos; sin argumento de línea de comandos).

---

## 6.2. Estructura del proyecto

```
proyectoGem5/
├── matrices_secuencial.c      Programa secuencial (TAM 100, sin hilos)
├── matrices_paralelo.c        Programa paralelo (pthreads, NUM_HILOS=#define=1)
├── Graficas.py                Gráficas speedup/IPC/miss/simTicks (valores hardcodeados)
├── EficienciaParalela.py       Gráfica eficiencia = speedup/hilos (valores hardcodeados)
├── estadisticas.xlsx           Tabla manual con métricas extraídas vía Select-String
├── Secuencial.docx            Informe con capturas + gráficas (18 imágenes)
├── stats_secuencial.txt        Stats Gem5 secuenciales (1 núcleo)
├── cpu_1/  stats_{1,2,4}hilo.txt   Stats 1 núcleo × {1,2,4} hilos
├── cpu_2/  stats_{1,2,4}hilo.txt   Stats 2 núcleos × {1,2,4} hilos
└── cpu_4/  stats_{1,2,4}hilo.txt   Stats 4 núcleos × {1,2,4} hilos
```

**Ausencias relevantes (no existen en el proyecto):** `Makefile`/script de compilación, scripts de ejecución de Gem5, archivos de configuración de Gem5 (`.py` de config), `config.ini`/`config.json` (Gem5 los genera junto a `stats.txt`), `README`/documentación de metodología, e instrucciones de instalación de Gem5.

| Archivo | Función | Relación con requisitos | Estado |
|---|---|---|---|
| `matrices_secuencial.c` | Mult. matrices secuencial, mide con `clock()` | 4B | Implementado; sin verificación de resultado, TAM via `#define` |
| `matrices_paralelo.c` | Mult. matrices con pthreads, partición por filas | 4C | Implementado; `NUM_HILOS` en `#define` (recompilar p/ cambiar hilos); sin verificación vs secuencial |
| `stats_secuencial.txt` | Salida Gem5 secuencia | 4A,4E,5 | Real; 1 núcleo; ~63 M instrucciones |
| `cpu_{1,2,4}/stats_{1,2,4}hilo.txt` | Salidas Gem5 por config | 4A,4D,4E | Reales; confirman 1/2/4 núcleos |
| `estadisticas.xlsx` | Métricas tabuladas (extracción manual) | 4E,4F | Contiene datos reales pero con errores (CPU1 speedup mal normalizado, miss=TLB no caché) |
| `Graficas.py` | Gráficas speedup/IPC/miss/tiempo | 4F | Funciona pero datos hardcodeados; comentario admite "base corregida" |
| `EficienciaParalela.py` | Gráfica eficiencia paralela | 4F | Funciona; **valores de CPU1 incorrectos** |
| `Secuencial.docx` | Informe con capturas y gráficas | 5M9 | Presenta resultados; nombra "CPU3" donde el repo usa `cpu_4` (inconsistencia menor) |

---

## 6.3. Matriz de cumplimiento

Estados permitidos: **CUMPLIDO / PARCIAL / NO CUMPLIDO / NO VERIFICABLE**.

### Sección 4 — Requisitos funcionales y técnicos

| ID | Requisito | Estado | Evidencia | Archivo/Ruta | Observaciones |
|---|---|---|---|---|---|
| A1 | Instrucciones/mecanismos para instalar y compilar Gem5 en Linux | NO CUMPLIDO | No hay README, Makefile, ni script de build | — | El proyecto se desarrolló en Linux (los stats son reales) pero no documenta cómo se instaló/compiló Gem5 |
| A2 | Configuraciones para ejecutar simulaciones en Gem5 | NO CUMPLIDO | No hay archivos de config `.py` ni `config.ini`/`config.json` | — | Las configs se usaron (los stats lo prueban) pero no están en el repo; no es reproducible |
| A3 | Define correctamente el modelo de CPU utilizado | PARCIAL | Stats con `commitStats0`/`executeStats0`/`fetchStats0`/`numBranches`/`issuedInstType` → consistentes con **O3CPU** | `cpu_4/stats_4hilo.txt` | El modelo es O3 (apropiado), pero no está documentado ni hay config que lo declare explícitamente |
| A4 | Permite configurar 1, 2 y 4 núcleos | CUMPLIDO | 1/2/4 líneas `system.cpuN.numCycles` en `cpu_1/2/4` | `cpu_*/stats_*.txt` | Verificado en ejecución; las configs mismas faltan (ver A2) |
| A5 | Scripts de ejecución o automatización de simulaciones | NO CUMPLIDO | No hay scripts `.sh`/`.bat` ni `run*` | — | Reproducir el barrido requeriría escribir los scripts desde cero |
| A6 | Ejecuta los programas dentro de Gem5 (no solo en el host) | CUMPLIDO | Cabeceras `Begin/End Simulation Statistics`, `simTicks`, `hostSeconds`, `simFreq=1e12` | todos los `stats*.txt` | Confirmado: es ejecución en Gem5, no en Linux nativo |
| B1 | Secuencial sin pthreads ni paralelismo | CUMPLIDO | Triple bucle i,j,k; sin `pthread.h` | `matrices_secuencial.c` | — |
| B2 | Multiplicación de matrices correcta | CUMPLIDO | `C[i][j] += A[i][k]*B[k][j]`, C inicializada a 0 | `matrices_secuencial.c` | Algoritmo correcto |
| B3 | Permite definir/modificar el tamaño de matrices | PARCIAL | `#define TAM 100` | `matrices_secuencial.c` | Requiere recompilar; sin argumento por línea de comandos |
| B4 | Produce resultados verificables | PARCIAL | Calcula C pero nunca la imprime ni verifica | `matrices_secuencial.c` | No hay checksum ni impresión de C |
| B5 | Permite medir el tiempo de ejecución | CUMPLIDO | `clock()` y `CLOCKS_PER_SEC` | `matrices_secuencial.c` | Nota: `clock()` mide tiempo de CPU (no wall-clock); en Gem5 la métrica válida es `simSeconds` |
| B6 | Ejecutable en el entorno de simulación | CUMPLIDO | `stats_secuencial.txt` con ~63 M instrucciones, `system.cpu.numCycles` | `stats_secuencial.txt` | Corrió dentro de Gem5 (1 núcleo) |
| C1 | Uso correcto de `pthread_create` | CUMPLIDO | `pthread_create(&hilos[i],NULL,multiplicar,&datos[i])` | `matrices_paralelo.c` | — |
| C2 | Uso correcto de `pthread_join` | CUMPLIDO | Bucle de join sobre todos los hilos | `matrices_paralelo.c` | — |
| C3 | Distribución del trabajo entre hilos | CUMPLIDO | `filasPorHilo = TAM/NUM_HILOS`; `inicio/fin` por hilo | `matrices_paralelo.c` | Partición por filas |
| C4 | Posibilidad de configurar 1, 2 y 4 hilos | PARCIAL | `#define NUM_HILOS 1` | `matrices_paralelo.c` | Hay que editar el `#define` y recompilar; sin argumento en CLI |
| C5 | Sincronización adecuada | CUMPLIDO | `pthread_join` espera a todos los hilos antes de medir fin | `matrices_paralelo.c` | — |
| C6 | Ausencia de condiciones de carrera | CUMPLIDO | Cada hilo escribe filas disjuntas de C; A y B son solo lectura | `matrices_paralelo.c` | Sin escrituras compartidas |
| C7 | Ausencia de errores de acceso a memoria | CUMPLIDO | 100 divisible por 1,2,4 (sin resto); índices dentro de rango | `matrices_paralelo.c` | Sin desbordamientos para las configs usadas |
| C8 | Correcta distribución de filas/bloques | CUMPLIDO | Asignación contigua de filas `[inicio,fin)` | `matrices_paralelo.c` | — |
| C9 | Verificación paralelo == secuencial | NO CUMPLIDO | Ningún código compara resultados ni imprime checksum | ambos `.c` | No hay verificación de corrección |
| D1 | Configs 1c/1h, 2c/2h, 4c/4h | CUMPLIDO | 9 archivos stats (cpu_1/2/4 × 1/2/4 hilos) | `cpu_*/stats_*hilo.txt` | Todas las celdas existen |
| D2 | Ejecución secuencial de referencia | CUMPLIDO | `stats_secuencial.txt` | raíz | 1 núcleo, ~63 M instr. |
| D3 | Núcleos e hilos correctamente diferenciados | CUMPLIDO | `cpu_N` = núcleos; `stats_Nhilo` = hilos | estructura de dirs | Conceptos separados correctamente |
| D4 | Experimentos comparables (tamaño/datos/constantes) | NO CUMPLIDO | `cpu_1` ~1.9 M instr. vs `cpu_2/4` ~63 M; además 63M→32M→17M al subir hilos | `stats*.txt` (simInsts) | Workload inconsistente; el supuesto de trabajo constante no se cumple |
| E1 | Tiempo de ejecución | CUMPLIDO | `simSeconds`/`simTicks` en stats; `clock()` en código | `stats*.txt`, `*.c` | — |
| E2 | Ciclos de CPU | CUMPLIDO | `system.cpuN.numCycles` | `stats*.txt` | — |
| E3 | Instrucciones ejecutadas | CUMPLIDO | `simInsts` / `thread_0.numInsts` | `stats*.txt` | — |
| E4 | CPI (y CPI calculable) | CUMPLIDO | `system.cpuN.cpi`, `system.cpuN.ipc` | `stats*.txt` | O3 reporta cpi/ipc por núcleo |
| E5 | Fallos de caché | NO CUMPLIDO | No hay objetos L1/L2; solo `icache_port`/`dcache_port`→`membus`→`mem_ctrls` | `cpu_4/stats_4hilo.txt` | Sin caché configurada → no hay fallos de caché. Los "Misses" graficados son TLB |
| E6 | Speedup | PARCIAL | `speedup = simTicks(1h)/simTicks(Nh)` | `estadisticas.xlsx`, `Graficas.py` | Fórmula correcta, pero basada en workloads inconsistentes (D4) |
| E7 | Eficiencia paralela | PARCIAL | `eficiencia = speedup/hilos` | `EficienciaParalela.py` | CPU1 usa speedup mal normalizado → eficiencia de CPU1 errónea |
| E8 | Estadísticas de utilización del pipeline | PARCIAL | O3 expone `fetchStats0`/`executeStats0`/`commitStats0`/`numBranches` | `stats*.txt` | Existen pero **no se extraen ni usan** en el análisis |
| F1 | Extrae estadísticas de `stats.txt` | PARCIAL | Hoja con `Select-String simTicks ...` en sharedStrings | `estadisticas.xlsx` | Extracción manual y transcripción a mano, no parsing automático |
| F2 | Procesa automáticamente los resultados | NO CUMPLIDO | Listas literales en código (`speedup_cpu1=[...]`) | `Graficas.py`, `EficienciaParalela.py` | Valores hardcodeados; no leen archivos |
| F3 | Organiza resultados por configuración | CUMPLIDO | Directorios `cpu_1/2/4` y bloques por CPU en la hoja | estructura + `estadisticas.xlsx` | — |
| F4 | Genera gráficas comparativas | CUMPLIDO | 4 gráficas (speedup/IPC/miss/tiempo) + eficiencia | `Graficas.py`, `EficienciaParalela.py` | Se ejecutan (matplotlib) |
| F5 | Visualiza el speedup | CUMPLIDO | `graficar(...,"Speedup vs Número de Hilos",...)` | `Graficas.py` | — |
| F6 | Visualiza la eficiencia paralela | PARCIAL | Gráfica de eficiencia presente | `EficienciaParalela.py` | Datos de CPU1 incorrectos |
| F7 | Compara secuencial con multihilo | PARCIAL | Existe `stats_secuencial.txt` | — | No se grafica contra el secuencial; el speedup se normaliza por la propia base de cada CPU, no por el secuencial |
| F8 | Analiza comportamiento al aumentar núcleos/hilos | PARCIAL | Las gráficas lo permiten | `Graficas.py` | Válido solo si D4 se corrige; las inconsistencias debilitan las conclusiones |
| F9 | Gráficas a partir de datos reales (no simulados) | PARCIAL | Subyacente real (stats Gem5) | — | Pero hardcodeado en scripts, con "base corregida" manual y CPU1 mal en eficiencia |

### Sección 5 — Metodología

| ID | Paso metodológico | Estado | Evidencia | Observaciones |
|---|---|---|---|---|
| M1 | Configurar Gem5 con 1, 2 y 4 núcleos | CUMPLIDO | `numCycles` por núcleo (1/2/4) en stats | Hecho; faltan las configs en el repo |
| M2 | Compilar el programa secuencial | NO VERIFICABLE | Sin Makefile/artefactos; pero corrió en Gem5 | No se puede ver el proceso de build |
| M3 | Compilar el programa paralelo (pthreads) | NO VERIFICABLE | Sin Makefile; corrió en Gem5 | Ídem; necesita `-lpthread` |
| M4 | Ejecutar programas bajo las configs de Gem5 | CUMPLIDO | 10 `stats.txt` reales | — |
| M5 | Obtener estadísticas de cada ejecución | CUMPLIDO | `stats.txt` completos (`End Simulation Statistics`) | — |
| M6 | Medir tiempo de ejecución y fallos de caché | PARCIAL | Tiempo sí; fallos de caché no (sin cachés) | Ver E5 |
| M7 | Calcular speedup y eficiencia paralela | PARCIAL | Calculados, pero con errores (CPU1) y workloads inconsistentes | Ver E6/E7/D4 |
| M8 | Generar gráficas comparativas | CUMPLIDO | `Graficas.py`, `EficienciaParalela.py` | — |
| M9 | Analizar los resultados obtenidos | PARCIAL | `Secuencial.docx` con gráficas y tablas | El análisis descansa sobre datos con inconsistencias (D4/E7) |

---

## 6.4. Problemas encontrados

| # | Problema | Gravedad | Evidencia / Ruta |
|---|---|---|---|
| P1 | **Sin jerarquía de caché**: las CPUs van directo al bus de memoria. El requisito "fallos de caché" es insatisfacible; los "Misses" graficados son fallos de TLB de instrucción (`mmu.itb.exMisses`) mal etiquetados como caché. | CRÍTICA | `cpu_4/stats_4hilo.txt`: solo `membus.pktCount_...icache_port`/`dcache_port` → `mem_ctrls`; sin objetos `l1d`/`l1i`/`l2`. Valores 232/250/177/71 coinciden con `itb.exMisses` |
| P2 | **Workload no comparable entre configuraciones**: `cpu_1` ~1.9 M instr. vs `cpu_2`/`cpu_4` ~63 M (≈33×). Comparar CPU1 con CPU2/CPU4 en tiempo absoluto es inválido. | CRÍTICA | `stats_secuencial`=62 982 508; `cpu_1/stats_1hilo`=1 916 430; `cpu_2/stats_1hilo`=63 200 432 (simInsts) |
| P3 | **Trabajo no constante al variar hilos**: en `cpu_2`, simInsts cae 63M→32M→17M al pasar 1→2→4 hilos; en `cpu_4`, 63M→63M→48M. El supuesto de trabajo constante para speedup no se cumple → los speedup no son concluyentes. | CRÍTICA | `cpu_2/stats_{1,2,4}hilo.txt` simInsts |
| P4 | **Desequilibrio severo entre hilos**: `cpu0` (hilo principal) ~1.9 M instr. con CPI alto (27.8 en cpu_2/2h, 14.96 en cpu_4/4h), mientras los demás núcleos hacen ~15–30 M con CPI ~1.7–1.87. La partición por filas no se traduce en trabajo balanceado entre núcleos. | ALTA | `cpu_2/stats_2hilo.txt`: cpu0.thread_0=1 917 983 / cpu1=30 678 249; `cpu_4/stats_4hilo.txt`: cpu0=1 920 892 / cpu1-3≈15.3 M |
| P5 | **Datos hardcodeados y no automáticos**: los scripts no leen `stats.txt`; la hoja se llenó a mano con `Select-String`. `Graficas.py` comenta *"tomamos el más estable (último o base corregida)"* → manipulación manual de datos. | ALTA | `Graficas.py` (listas literales + comentario); `estadisticas.xlsx` sharedStrings con comandos `Select-String` |
| P6 | **Inconsistencia de speedup de CPU1 entre fuentes**: `Graficas.py`=[1, 0.99937, 1]; `EficienciaParalela.py`=[1.000626834, 1.001244372, 1.0]; hoja=`speedup Hilo4`=[1.001872, 1.001244, 1]. La eficiencia de CPU1 se calcula con una normalización desplazada (T2/T1, T4/T2, 1). | ALTA | `Graficas.py` vs `EficienciaParalela.py` vs `estadisticas.xlsx` |
| P7 | **Sin verificación de corrección**: ni el secuencial ni el paralelo imprimen/verifican el resultado; no se comprueba que paralelo == secuencial. | ALTA | `matrices_secuencial.c`, `matrices_paralelo.c` (no imprimen C) |
| P8 | **`NUM_HILOS` como `#define` (=1)**: cambiar hilos exige editar y recompilar; sin argumento CLI. Propenso a usar el binario equivocado por config. | MEDIA | `matrices_paralelo.c`: `#define NUM_HILOS 1` |
| P9 | **`clock()` para medir paralelo**: mide tiempo de CPU agregado, no wall-clock; en paralelo puede crecer con los hilos. No afecta al speedup (que usa `simTicks`), pero la salida impresa del programa es engañosa. | MEDIA | `matrices_paralelo.c` (`clock()`) |
| P10 | **Faltan configs/scripts de Gem5**: no hay `.py` de configuración, ni `config.ini/json`, ni scripts de ejecución/compilación. El experimento no es reproducible a partir del repo. | ALTA | Inventario de archivos (ningún `.sh`/`Makefile`/`config*`) |
| P11 | **Sin documentación de metodología/instalación**: no hay README ni instrucciones de Gem5. | MEDIA | Sin `README*` ni `*.md` |
| P12 | **Pipeline O3 no aprovechado**: existen estadísticas detalladas de fetch/execute/commit y `numBranches`, pero no se extraen ni analizan. | MEDIA | `stats*.txt` (`executeStats0`, `numBranches`) |
| P13 | **Inconsistencia de etiquetado**: el documento nombra "CPU3" donde el repo usa `cpu_4` (4 núcleos). | BAJA | `Secuencial.docx` (texto "CPU3:") vs directorio `cpu_4` |
| P14 | **Speedup normalizado por la base de cada CPU, no por el secuencial**: las gráficas no comparan contra la referencia secuencial. | MEDIA | `Graficas.py` (cada serie parte de 1 en su propio 1-hilo) |

---

## 6.5. Análisis de viabilidad

**Lo que funciona actualmente (verificado).**

- Los dos programas en C compilan conceptualmente y **ya se ejecutaron dentro de Gem5** (los `stats.txt` lo demuestran). El secuencial y el paralelo corren en modo emulación de llamadas al sistema (SE) de Gem5, y los pthreads funcionaron (los simInsts de `cpu_1` crecen levemente con los hilos, coherente con el overhead de creación/join).
- Las 3 configuraciones de núcleos (1/2/4) y los 3 conteos de hilos (1/2/4) están materializados en estadísticas reales.
- La generación de gráficas funciona (matplotlib) y produce las visualizaciones pedidas.
- El modelo O3 es apropiado y está efectivamente en uso.

**Lo que necesita correcciones.**

- **Configuración de Gem5**: añadir cachés L1/L2 para poder medir fallos de caché reales (P1); mantener el workload idéntico entre configs (P2, P3).
- **Programas en C**: `NUM_HILOS` y `TAM` por argumento CLI (P8); imprimir/verificar C y comparar paralelo vs secuencial (P7); usar wall-clock coherente y dejar la métrica oficial en `simSeconds` (P9).
- **Datos y scripts**: reemplazar valores hardcodeados por lectura automática de `stats.txt` (P5); corregir la normalización de CPU1 en `EficienciaParalela.py` (P6).

**Lo que necesita implementarse desde cero.**

- Scripts de compilación (Makefile) y de ejecución de Gem5 (P10).
- Archivos de configuración de Gem5 (con cachés) y su documentación (P10, P11).
- Un extractor/procesador automático de `stats.txt` → CSV → gráficas (P5).
- Verificación de resultados (P7).

**Lo que depende de herramientas externas.**

- Gem5 (no presente en este entorno Windows de auditoría; el proyecto se hizo en Linux). Su ausencia aquí es **una limitación del entorno de auditoría, no del código**: los stats reales demuestran que sí se contaba con Gem5 al generarlos. Para reproducir hace falta instalar Gem5 + toolchain (g++/arm-none) en Linux, lo cual está fuera del repo.

---

## 6.6. Plan de trabajo recomendado

### Prioridad crítica

1. **Reconfigurar Gem5 con jerarquía de caché (L1I/L1D/L2).** Sin cachés no hay fallos de caché y el CPI es artificialmente alto. *Archivos a crear:* configs `.py` de Gem5 (p. ej. basados en `configs/example/se.py` o uno propio) con `L1ICache`/`L1DCache`/`L2Cache`. *Verificación:* en `stats.txt` deben aparecer `l1i`/`l1d`/`l2` con `demandMisses`/`overallMisses` distintos de cero.
2. **Unificar el workload entre configuraciones.** Usar el mismo `TAM` y los mismos datos para 1/2/4 núcleos e hilos. *Archivos:* pasar `TAM` y `NUM_HILOS` por argumento (`argv`) en ambos `.c`. *Verificación:* `simInsts` debe ser ≈ constante al variar hilos y comparable entre configs (misma magnitud en `cpu_1/2/4`).
3. **Revisar el mapeo hilos→núcleos para balancear carga.** Confirmar que los N hilos de trabajo se distribuyen en N núcleos y que el hilo principal no acapara un núcleo ocioso. *Verificación:* `thread_0.numInsts` similar entre todos los núcleos activos (no 1.9 M vs 15–30 M).

### Prioridad alta

4. **Crear scripts de compilación y ejecución.** Un `Makefile` (`gcc -O2 -lpthread`) y un `run_gem5.sh` que recorra 1/2/4 núcleos × 1/2/4 hilos, generando `stats.txt` y `config.ini`. *Verificación:* ejecutar el script produce los 9 (o 10 con secuencial) `stats.txt`.
5. **Verificación de resultados.** Imprimir un checksum de C (suma o elemento de control) en ambos programas y comparar paralelo vs secuencial. *Verificación:* el programa aborte o avise si difieren.
6. **Extractor automático de estadísticas.** Un script (Python) que lea cada `stats.txt`, extraiga `simSeconds`, `simTicks`, `simInsts`, `numCycles`, `cpi`, `ipc` y `l1d/l1i/l2` misses, y genere un CSV. *Verificación:* los valores coinciden con `Select-String` sobre los archivos.
7. **Recomputar speedup y eficiencia desde el CSV** con `speedup = simTicks_seq / simTicks_N` (base secuencial) y `eficiencia = speedup/hilos`. *Verificación:* las gráficas se regeneran sin valores hardcodeados; CPU1 deja de mostrar eficiencia ≈1 espuria.

### Prioridad media

8. **Corregir `EficienciaParalela.py`**: usar normalización correcta para CPU1 (1, T1/T2, T1/T4) y eliminar la inconsistencia con `Graficas.py` (P6).
9. **Aprovechar estadísticas O3**: extraer `numBranches`, `branchMispredicts`, IPC por etapa y añadir gráficas de utilización del pipeline (P12).
10. **Documentar metodología e instalación**: un `README.md` con pasos de Gem5, compilación, ejecución y análisis (P11).

### Mejoras adicionales

11. Comparar explícitamente contra la referencia secuencial en una misma gráfica (P14).
12. Unificar etiquetado "CPU3/CPU4" en el documento (P13).
13. Sembrar `rand()` deliberadamente (o usar datos fijos) y documentarlo, para garantizar reproducibilidad.

---

## 6.7. Evaluación final

**Ponderación explícita.** Se evalúan los 51 requisitos de las secciones 4 y 5 con **peso 1 cada uno**. Estado → puntaje: CUMPLIDO = 1.0, PARCIAL = 0.5, NO CUMPLIDO = 0. Los **NO VERIFICABLE se excluyen del denominador** (no son requisitos verificables). Los NO CUMPLIDO por ausencia de Gem5 en *este* entorno de auditoría no aplican: los stats reales prueban que Gem5 sí estuvo disponible al generarlos, por lo que las carencias de configs/scripts son deficiencias del proyecto, no del entorno.

**Conteo por estado.**

| Estado | Cantidad |
|---|---:|
| CUMPLIDO | 27 |
| PARCIAL | 15 |
| NO CUMPLIDO | 7 |
| NO VERIFICABLE | 2 |
| **Total** | **51** |

Requisitos verificables = 51 − 2 = **49**.
Puntaje ponderado = 27×1.0 + 15×0.5 + 7×0 = **34.5**.

| Categoría | CUMPLIDO | PARCIAL | NO CUMPLIDO | NO VERIF. | Puntaje / Verificables |
|---|---:|---:|---:|---:|---|
| A. Integración Gem5 (6) | 2 | 1 | 3 | 0 | 2.5 / 6 |
| B. Secuencial (6) | 4 | 2 | 0 | 0 | 5.0 / 6 |
| C. Paralelo (9) | 7 | 1 | 1 | 0 | 7.5 / 9 |
| D. Experimentos (4) | 3 | 0 | 1 | 0 | 3.0 / 4 |
| E. Métricas (8) | 4 | 3 | 1 | 0 | 5.5 / 8 |
| F. Análisis/visualización (9) | 3 | 5 | 1 | 0 | 5.5 / 9 |
| M. Metodología (9) | 4 | 3 | 0 | 2 | 5.5 / 7 |

**Porcentaje de cumplimiento (sobre requisitos verificables):** 34.5 / 49 = **70.4 %**.

- Requisitos cumplidos: **27**
- Requisitos parciales: **15**
- Requisitos no cumplidos: **7**
- Requisitos no verificables: **2**

**Principales obstáculos para completar el proyecto.**

1. **Ausencia de configuración de caché en Gem5** (bloquea el requisito de fallos de caché y distorsiona el CPI).
2. **Workloads inconsistentes entre configuraciones y entre conteos de hilos** (invalida la comparabilidad y la validez del speedup).
3. **Falta de automatización y de artefactos de reproducibilidad** (no hay configs, Makefile, scripts ni extractor automático; los gráficos dependen de datos a mano con errores conocidos).
4. **Procesamiento manual de datos con inconsistencias** (CPU1 mal normalizado en eficiencia; "base corregida" a ojo).

**Conclusión.** El proyecto *ejecutó* el experimento dentro de Gem5 y dispone de estadísticas reales, lo que lo sitúa por encima del 50 % de cumplimiento; pero la ausencia de cachés, la no comparabilidad de los workloads y el carácter manual/inconsistente del análisis impiden considerarlo metodológicamente válido tal como está. Corrigiendo los tres puntos críticos de la sección 6.6 (cachés, workload único y balanceo de hilos) y automatizando la extracción, el proyecto alcanzaría un cumplimiento pleno y reproducible.

---

# ANEXO — Resumen en 3 preguntas

## A. ¿Qué cumple realmente?

El proyecto **sí corre dentro de Gem5** (no es un fraude: los `stats.txt` son salidas reales de Gem5) y cumple lo **ejecutable**, pero **no cumple lo metodológico**.

**Sí cumple:**

- Ejecuta el secuencial y el paralelo dentro de Gem5 (verificado en los 10 `stats.txt`).
- Usa el modelo **O3CPU** (el detallado, apropiado para este estudio).
- Configura **1, 2 y 4 núcleos** de verdad (1/2/4 líneas `numCycles` en los stats).
- El programa paralelo es **correcto y sin carreras**: usa bien `pthread_create`/`pthread_join`, reparte filas, y como cada hilo escribe filas distintas no hay condición de carrera.
- Genera las gráficas pedidas (speedup, eficiencia, IPC, tiempo).
- Calcula speedup y eficiencia.

**No cumple (lo importante):**

- **No hay fallos de caché**: la config de Gem5 no tenía cachés (las CPUs van directas a memoria). Los "Misses" de la gráfica son en realidad **fallos de TLB mal etiquetados**.
- **Los experimentos no son comparables**: `cpu_1` corrió una matriz ~33× más chica que `cpu_2`/`cpu_4`, y al subir hilos las instrucciones *bajan* (deberían mantenerse). → el speedup es dudoso.
- **No verifica** que el resultado paralelo sea igual al secuencial.
- Los datos de las gráficas están **escritos a mano** (no se leen de los stats) y tienen **errores** (la eficiencia de CPU1 está mal calculada).

En números: **~70 % de cumplimiento** (27 cumplidos, 15 parciales, 7 no cumplidos, 2 no verificables).

## B. ¿Qué archivos son necesarios?

**Lo que ya existe y sirve:**

- `matrices_secuencial.c`, `matrices_paralelo.c` — los programas (con arreglos menores).
- Los 10 `stats.txt` (secuencial + `cpu_1/2/4` × 1/2/4 hilos) — resultados reales.
- `Graficas.py`, `EficienciaParalela.py` — generan gráficas (hay que quitarles los datos a mano).
- `estadisticas.xlsx`, `Secuencial.docx` — tablas e informe.

**Lo que FALTA y hay que crear:**

| Archivo a crear | Para qué |
|---|---|
| **Config de Gem5** (`.py`, p. ej. `config_multicore.py`) | Definir 1/2/4 núcleos **con cachés L1/L2** (sin esto no hay fallos de caché) |
| `Makefile` | Compilar ambos `.c` (el paralelo con `-lpthread`) |
| `run_gem5.sh` | Automatizar el barrido 1/2/4 núcleos × 1/2/4 hilos |
| `extraer_stats.py` | Leer los `stats.txt` y armar un CSV automáticamente (reemplaza el transcription a mano) |
| `README.md` | Documentar instalación de Gem5, compilación, ejecución y análisis |

Y en los `.c` ya existentes: cambiar `TAM` y `NUM_HILOS` de `#define` a **argumentos de línea de comandos**, y añadir **verificación del resultado** (checksum de C).

## C. ¿Cómo funciona (el flujo)?

Así está planteado ahora, y así **debería** ser una vez arreglado:

1. **Configuras Gem5** con N núcleos (1, 2 o 4) — un archivo `.py` define la CPU (O3), los núcleos, las cachés y la memoria.
2. **Compilás** los programas: el secuencial normal, el paralelo con pthreads.
3. **Ejecutás** cada programa dentro de Gem5 con esa config. Gem5 corre tu binario en su CPU simulada y, al terminar, vuelca todo a `stats.txt` (tiempo simulado, ciclos, instrucciones, CPI, fallos de caché, etc.).
4. **Repetís** la combinación núcleos×hilos: 1c/1h, 2c/2h, 4c/4h (más el secuencial de referencia), **manteniendo igual el tamaño de matriz y los datos**.
5. **Extraés** las métricas de cada `stats.txt` (hoy a mano con `Select-String`; debería ser automático).
6. **Calculás** `speedup = tiempo_1hilo / tiempo_Nhilos` y `eficiencia = speedup / hilos`.
7. **Generás** las gráficas comparativas (speedup, eficiencia, fallos de caché, IPC) a partir de esos datos.
8. **Analizás**: si al subir hilos el tiempo baja y la eficiencia se mantiene alta, el multihilo aprovecha los núcleos.

El quid del asunto es que **Gem5 simula el procesador** (no ejecuta tu programa en Linux normal): por eso los `stats.txt` traen `simTicks`, `numCycles`, `cpi`… que son del procesador simulado, no del hardware real. Esa es justamente la diferencia clave que el proyecto respeta: sí corrió dentro de Gem5.
