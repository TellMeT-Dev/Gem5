# MANUAL DE SUSTENTACIÓN — Multiplicación de matrices multi-hilo en Gem5

> Documento de apoyo para la sustentación. Contiene: qué hace el proyecto,
> cómo funciona, cómo se ejecuta, los resultados reales y las preguntas
> probables del jurado con sus respuestas.
>
> **Todos los números de este documento provienen directamente de los archivos
> `stats.txt` generados por Gem5 y del archivo `metricas.csv`. No hay valores
> inventados.**

---

## 1. En 30 segundos (la respuesta corta)

**Qué es:** un experimento que mide cómo se comporta un procesador simulado
(**Gem5**, modelo **TimingSimpleCPU**) al ejecutar una multiplicación de
matrices 100×100 de forma **secuencial** y de forma **paralela con pthreads**,
variando el número de **núcleos** (1, 2, 4) y de **hilos** (1, 2, 4).

**Qué produce:** 8 archivos de estadísticas reales de Gem5 + métricas extraídas
automáticamente + gráficas de speedup, eficiencia, fallos de caché e IPC.

**Resultado central:** con 2 núcleos y 2 hilos se logra un **speedup de 1.47×**
respecto al mismo programa con 1 hilo en la misma CPU. Los fallos de caché L1D
son los más importantes (~31 000–32 000 por corrida), con una L2 compartida que
absorbe solo ~2 000 fallos.

---

## 2. Estructura del proyecto

```
proyectoGem5/
├── Makefile                     Compilación de los .c
├── run_gem5.sh                  Barrido automático núcleos × hilos
├── config_multicore.py          Config de Gem5 con jerarquía L1I/L1D/L2
│
├── matrices_secuencial.c        Multiplicación sin hilos
├── matrices_paralelo.c          Multiplicación con pthreads
│
├── extraer_stats.py             stats.txt → metricas.csv
├── Graficas.py                  Gráficas comparativas (8 PNG)
├── EficienciaParalela.py        Gráfica de eficiencia paralela
├── metricas.csv                 (se regenera con extraer_stats.py)
│
├── stats_secuencial.txt         Referencia secuencial (1 núcleo)
├── cpu1_1hilo.txt  cpu1_2hilo.txt  cpu1_4hilo.txt   1 núcleo  × 1/2/4 hilos
├── cpu2_1hilo.txt  cpu2_2hilo.txt                   2 núcleos × 1/2 hilos
├── cpu4_1hilo.txt  cpu4_2hilo.txt                   4 núcleos × 1/2 hilos
│
├── manuales/
│   ├── MANUAL_SUSTENTACION.md   Este archivo
│   ├── Secuencial.docx          Informe con capturas y gráficas
│   └── estadisticas.xlsx        Tabla resumen
│
└── documentacion/
    ├── README.md                Cómo instalar y usar
    └── AUDITORIA.md             Auditoría técnica del proyecto
```

**Nota:** los configs 2c/4t y 4c/4t no tienen archivo `stats.txt` porque
`TimingSimpleCPU` no soporta SMT con múltiples núcleos activos simultáneos
(produce un assertion en gem5); están documentados como limitación conocida.

---

## 3. Cómo funciona (el flujo completo)

```
   ┌─────────────────────┐
   │  1. COMPILAR        │   make
   │     los .c          │   → matrices_secuencial, matrices_paralelo
   └─────────┬───────────┘
             ▼
   ┌─────────────────────┐
   │  2. SIMULAR         │   ./run_gem5.sh /ruta/gem5.opt
   │     en Gem5         │   → por cada config: stats_*.txt
   └─────────┬───────────┘
             ▼
   ┌─────────────────────┐
   │  3. EXTRAER         │   python3 extraer_stats.py
   │     métricas        │   → metricas.csv (8 filas)
   └─────────┬───────────┘
             ▼
   ┌─────────────────────┐
   │  4. GRAFICAR        │   python3 Graficas.py
   │                     │   python3 EficienciaParalela.py
   └─────────┬───────────┘   → 8 archivos *.png
             ▼
   ┌─────────────────────┐
   │  5. ANALIZAR        │   speedup, eficiencia, IPC, fallos de caché
   └─────────────────────┘
```

### Qué hace cada programa en C

Ambos multiplican `C = A × B` con matrices de **100×100** de enteros.

**`matrices_secuencial.c`** — triple bucle clásico, sin hilos:

```c
for (i = 0; i < TAM; i++)
  for (j = 0; j < TAM; j++)
    for (k = 0; k < TAM; k++)
      C[i][j] += A[i][k] * B[k][j];
```

**`matrices_paralelo.c`** — reparte las **filas** entre N hilos:

```c
filasPorHilo = TAM / NUM_HILOS;        // 100 / N = filas por hilo

datos[i].inicio = i * filasPorHilo;    // fila inicial del hilo i
datos[i].fin    = (i + 1) * filasPorHilo;

pthread_create(&hilos[i], NULL, multiplicar, &datos[i]);  // lanzar
pthread_join(hilos[i], NULL);                              // esperar
```

**Por qué no hay condición de carrera:** cada hilo escribe filas **disjuntas**
de `C`, y `A`/`B` solo se leen. No hay escrituras compartidas.

**Por qué 100 es un tamaño válido:** 100 es divisible entre 1, 2 y 4, así que
la partición no deja filas sin cubrir.

---

## 4. Cómo ejecutarlo (demo en vivo)

```bash
# 1. Compilar los programas en C
make

# 2. Verificar que corren nativamente
./matrices_secuencial
./matrices_paralelo

# 3. Extraer métricas de los stats.txt existentes (no necesita Gem5)
python3 extraer_stats.py

# 4. Generar gráficas (requiere matplotlib)
python3 Graficas.py
python3 EficienciaParalela.py
```

Para **re-simular desde cero** con Gem5 (requiere gem5.opt):

```bash
./run_gem5.sh /run/media/tellmedev/Externo/gem5/build/X86/gem5.opt
```

> **Tip para la sustentación:** si no hay tiempo o falta `matplotlib`, basta
> con `python3 extraer_stats.py` — imprime speedup y eficiencia en pantalla.

---

## 5. Resultados reales (números para citar)

Todos los valores provienen del archivo `metricas.csv`, que se genera
automáticamente leyendo los `stats.txt` de Gem5.

### 5.1 Referencia secuencial

| Métrica | Valor |
|---|---|
| `simTicks` | 3 191 337 468 |
| `simInsts` | 5 502 973 |
| Ciclos totales | 9 583 596 |
| **IPC** | **0.5742** |
| Fallos L1D | 27 632 |
| Fallos L1I | 731 |
| Fallos L2 | 1 326 |

### 5.2 Tabla completa de configuraciones

| Núcleos | Hilos | simTicks | simInsts | IPC | L1D misses | L2 misses |
|---:|---:|---:|---:|---:|---:|---:|
| SEC | - | 3 191 337 468 | 5 502 973 | 0.5742 | 27 632 | 1 326 |
| 1 | 1 | 3 579 834 915 | 6 167 547 | 0.5048 | 31 810 | 1 996 |
| 1 | 2 | 3 525 582 555 | 6 179 351 | 0.3424 | 19 323 | 2 052 |
| 1 | 4 | 3 510 858 627 | 6 202 864 | 0.2072 | 12 933 | 2 151 |
| 2 | 1 | 3 557 969 802 | 6 167 561 | 0.2899 | 31 876 | 1 994 |
| 2 | 2 | 2 424 299 607 | 6 179 498 | 0.3046 | 32 009 | 2 173 |
| 4 | 1 | 3 557 969 802 | 6 167 561 | 0.2899 | 31 876 | 1 994 |
| 4 | 2 | 2 412 514 737 | 6 179 531 | 0.2862 | 32 079 | 2 206 |

> **Dato importante de consistencia:** `simInsts` es comparable entre todas las
> configuraciones (~6.17–6.20 M en las paralelas), lo que confirma que todas
> ejecutan exactamente el mismo trabajo. Las diferencias en `simTicks` reflejan
> genuinamente diferencias de tiempo de ejecución.

### 5.3 Speedup y eficiencia

**Speedup interno** (base = 1 hilo de la misma CPU — el más útil para comparar):

| Núcleos | Hilos | simTicks | Speedup | Eficiencia |
|---:|---:|---:|---:|---:|
| 1 | 1 | 3 579 834 915 | 1.000 | 1.000 |
| 1 | 2 | 3 525 582 555 | 1.015 | 0.508 |
| 1 | 4 | 3 510 858 627 | 1.020 | 0.255 |
| 2 | 1 | 3 557 969 802 | 1.000 | 1.000 |
| **2** | **2** | 2 424 299 607 | **1.468** | **0.734** |
| 4 | 1 | 3 557 969 802 | 1.000 | 1.000 |
| **4** | **2** | 2 412 514 737 | **1.475** | **0.737** |

**Speedup vs referencia secuencial** (base = programa secuencial):

| Núcleos | Hilos | Speedup vs SEC |
|---:|---:|---:|
| 1 | 1 | 0.891 |
| 1 | 2 | 0.905 |
| 1 | 4 | 0.909 |
| 2 | 1 | 0.897 |
| 2 | 2 | **1.316** |
| 4 | 1 | 0.897 |
| 4 | 2 | **1.323** |

> **Por qué el paralelo es más lento que el secuencial en 1 hilo:** el programa
> paralelo tiene overhead de `pthread_create` y `pthread_join` incluso con
> un solo hilo. Con TAM=100 el trabajo total es pequeño, así que ese overhead
> pesa relativamente más. Es un resultado esperado y correcto.

### 5.4 Fallos de caché (L1D + L1I + L2)

| Núcleos | Hilos | L1D misses | L1I misses | L2 misses | Total caché |
|---:|---:|---:|---:|---:|---:|
| SEC | - | 27 632 | 731 | 1 326 | 29 689 |
| 1 | 1 | 31 810 | 1 126 | 1 996 | 34 932 |
| 1 | 2 | 19 323 | 1 134 | 2 052 | 22 509 |
| 1 | 4 | 12 933 | 1 134 | 2 151 | 16 218 |
| 2 | 1 | 31 876 | 1 215 | 1 994 | 35 085 |
| 2 | 2 | 32 009 | 1 346 | 2 173 | 35 528 |
| 4 | 1 | 31 876 | 1 215 | 1 994 | 35 085 |
| 4 | 2 | 32 079 | 1 431 | 2 206 | 35 716 |

> **Patrón interesante en 1 núcleo (SMT):** los fallos L1D bajan al aumentar
> los hilos (31 810 → 19 323 → 12 933). Con SMT los hilos comparten la L1D
> del mismo núcleo: cuando un hilo ya cargó una línea de caché, el otro hilo
> puede reutilizarla sin volver a memoria. Eso es **reutilización de caché
> compartida**.
>
> **En múltiples núcleos** (2c y 4c) los fallos L1D se mantienen constantes
> (~31 900–32 000) porque cada núcleo tiene su propia L1D privada; no hay
> reutilización entre núcleos.

---

## 6. Conclusiones que puedes defender

1. **El paralelismo funciona con múltiples núcleos.** Con 2 núcleos y 2 hilos
   el tiempo cae de 3 558 M a 2 424 M de ticks → **speedup 1.47×**, con
   eficiencia de **0.73**. Con 4 núcleos el resultado es casi idéntico (1.47×),
   lo que muestra que el cuello de botella no está en los núcleos sino en el
   trabajo disponible (TAM=100 es una carga pequeña).

2. **Con 1 núcleo (SMT) el paralelismo aporta poco.** Speedup ≈ 1.02 con 4
   hilos, porque los hilos compiten por el mismo núcleo físico. El único
   beneficio visible es la **reducción de fallos de caché L1D** (31 810 →
   12 933) por reutilización de la caché compartida entre contextos SMT.

3. **La eficiencia es 0.73 con 2 núcleos.** El 27% de pérdida se debe al
   overhead de `pthread_create`/`pthread_join`, al hilo principal (que hace
   trabajo secuencial: inicializar matrices, crear hilos, hacer join) y a que
   TAM=100 es un problema pequeño para el número de hilos.

4. **La jerarquía de caché L1/L2 está presente y medida.** Los fallos de L1D
   (~31 800 por corrida) y L2 (~2 000) son estadísticas reales de gem5,
   extraídas de las claves `board.cache_hierarchy.l1dcaches*.demandMisses`.

5. **Los workloads son comparables.** `simInsts` es constante (~6.17–6.20 M)
   en todas las configuraciones paralelas, confirmando que todas resuelven el
   mismo problema de tamaño idéntico. El speedup interno es por tanto válido.

---

## 7. Preguntas probables del jurado

| # | Pregunta | Respuesta breve |
|---|---|---|
| 1 | **¿Qué es Gem5?** | Simulador de arquitectura que modela el procesador ciclo a ciclo. No ejecuta en el CPU real; por eso `stats.txt` tiene `simTicks` (tiempo simulado) y `numCycles`. |
| 2 | **¿Por qué TimingSimpleCPU?** | Modela la latencia real de acceso a caché (accesos bloqueantes con tiempo de respuesta), lo que da `simTicks` significativos. O3CPU es más detallado pero ~50× más lento en gem5; no es viable para un barrido completo. |
| 3 | **¿Qué diferencia hay entre núcleo e hilo?** | Núcleo = unidad física de ejecución. Hilo = flujo de instrucciones software. Aquí se miden por separado: `cpu_N` = núcleos físicos, `N_hilo` = hilos software con pthreads. |
| 4 | **¿Cómo se reparte el trabajo?** | Por filas: el hilo `i` calcula las filas `[i·TAM/N, (i+1)·TAM/N)`. Con 2 hilos: hilo 0 → filas 0–49, hilo 1 → filas 50–99. Cada hilo escribe filas distintas → sin condición de carrera. |
| 5 | **¿Qué es speedup?** | `T₁ / Tₙ`: tiempo con 1 hilo dividido entre tiempo con N hilos. Speedup 1.47 significa que con 2 núcleos el programa tarda el 68% del tiempo original. |
| 6 | **¿Qué es eficiencia paralela?** | `speedup / N_hilos`. Cuánto de la capacidad teórica se aprovecha. Eficiencia 1.0 = perfecto. Aquí 0.73 = se aprovecha el 73% con 2 núcleos/2 hilos. |
| 7 | **¿Qué es IPC?** | Instrucciones por ciclo. Mayor IPC = procesador más eficiente. El secuencial tiene IPC=0.57; el paralelo cae a 0.29–0.50 porque hay overhead de pthreads y esperas. |
| 8 | **¿Por qué el paralelo con 1 hilo es más lento que el secuencial?** | El programa paralelo tiene overhead de `pthread_create` y `pthread_join`. Con TAM=100 el trabajo total es pequeño, así ese overhead pesa más que el beneficio. |
| 9 | **¿Por qué 4 núcleos y 2 núcleos dan casi el mismo speedup?** | El cuello de botella es el volumen de trabajo (TAM=100 × 100 × 100 = 1 000 000 operaciones), no la cantidad de núcleos. Con solo 2 hilos activos, agregar más núcleos no ayuda. |
| 10 | **¿Qué son los fallos de caché?** | Cuando el procesador busca un dato en L1 y no está, debe ir a L2 o a memoria principal (más lento). Los ~31 800 fallos L1D por corrida son accesos a las matrices A y B que no están en caché. |
| 11 | **¿Por qué bajan los fallos L1D con más hilos en 1 núcleo?** | Con SMT, los hilos comparten la L1D del mismo núcleo. Si un hilo cargó una línea de caché, el otro hilo la puede reutilizar. Con múltiples núcleos no pasa esto (cada uno tiene su L1 privada). |
| 12 | **¿Los datos son reales o inventados?** | Reales: los `stats.txt` contienen la cabecera `Begin Simulation Statistics`, `simFreq = 1 000 000 000 000`, `hostSeconds` (tiempo real de simulación). Los generó `run_gem5.sh` con gem5.opt. |
| 13 | **¿Cómo se calcularon las gráficas?** | `extraer_stats.py` parsea los `stats.txt` → `metricas.csv`. Los scripts de Python leen el CSV y grafican. No hay valores hardcodeados. |
| 14 | **¿Qué medirías si tuvieras más tiempo?** | Aumentar TAM (500×500) para que el paralelo supere más al secuencial, y probar O3CPU para ver el efecto del pipeline fuera de orden en las instrucciones de branch. |

---

## 8. Limitaciones conocidas (y cómo responderlas)

### "Solo hay 8 de las 10 configuraciones posibles"

**Sí, es correcto.** Faltan `cpu2_4hilo.txt` y `cpu4_4hilo.txt`. Con
`TimingSimpleCPU`, usar SMT (múltiples hilos por núcleo) en una configuración
multicore produce un assertion en gem5 (`recvTimingResp: Assertion
'!tickEvent.scheduled()'`). El modelo O3 sí los soporta pero es ~50× más lento
(cada simulación tarda >10 minutos). Se priorizó obtener 8 configs funcionales
con datos reales sobre esperar horas por los 2 configs restantes.

### "El secuencial simple es más rápido que el paralelo con 1 hilo"

**Sí, y es correcto.** El programa secuencial usa un triple bucle sin overhead
de pthreads. El paralelo con 1 hilo llama a `pthread_create`/`pthread_join`
incluyendo asignación de pila, contexto de hilo, etc. Con TAM=100 ese overhead
supera el "beneficio" de la paralelización vacía. Con TAM más grande el
paralelo ganaría.

### "TAM y NUM_HILOS están en el .c como #define"

**Sí, se mantiene a propósito** (decisión de alcance del proyecto). El script
`run_gem5.sh` genera automáticamente una copia temporal con el `#define`
correcto para cada corrida, sin modificar el `.c` original.

---

## 9. Comandos de emergencia

```bash
# Compilar y verificar que funciona nativamente
make
./matrices_secuencial
./matrices_paralelo

# Extraer métricas e imprimir speedup/eficiencia en pantalla
python3 extraer_stats.py

# Regenerar todas las gráficas
python3 Graficas.py
python3 EficienciaParalela.py

# Ver fallos de caché de una config
grep -E '\.demandMisses::total' cpu2_2hilo.txt

# Ver una métrica puntual
grep "^simTicks" cpu2_2hilo.txt
grep "^simInsts" cpu2_2hilo.txt

# Re-simular desde cero (requiere gem5.opt)
./run_gem5.sh /run/media/tellmedev/Externo/gem5/build/X86/gem5.opt
```

---

*Documento generado sobre los datos reales del barrido con `run_gem5.sh`
(gem5 v25.1, TimingSimpleCPU, X86, L1I/L1D 32 KiB, L2 256 KiB, DDR4-2400 1 GiB, 3 GHz).*
