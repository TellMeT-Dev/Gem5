#!/usr/bin/env bash
# =============================================================================
# run_gem5.sh — Barrido automático de configuraciones en Gem5
# =============================================================================
# Recorre la matriz  núcleos {1,2,4}  ×  hilos {1,2,4}  más la referencia
# secuencial, y deja cada salida en esta misma carpeta:
#
#     stats_secuencial.txt
#     cpu1_1hilo.txt  cpu1_2hilo.txt  cpu1_4hilo.txt
#     cpu2_1hilo.txt  cpu2_2hilo.txt  cpu2_4hilo.txt
#     cpu4_1hilo.txt  cpu4_2hilo.txt  cpu4_4hilo.txt
#
# Requisitos:
#   - gem5.opt compilado   (ver documentacion/README.md)
#   - make estatico        (binarios estáticos para modo SE)
#   - config_multicore.py  (config con jerarquía L1/L2)
#
# Uso:
#   ./run_gem5.sh /ruta/a/gem5.opt
#   ./run_gem5.sh            # usa GEM5_BIN del PATH
#
# NOTA sobre NUM_HILOS (AUDITORIA P8):
#   El código fuente usa "#define NUM_HILOS 1" y no acepta argv. Para poder
#   barrer 1/2/4 hilos SIN modificar el .c original, este script genera una
#   copia temporal con el valor deseado y la compila. El archivo original
#   queda intacto.
#
# NOTA sobre datos (AUDITORIA P2/P3):
#   matrices_*.c usa rand() sin srand(), lo que en C siempre arranca con la
#   semilla 1 → los datos son idénticos en TODAS las corridas. Además TAM=100
#   es fijo. Por eso simInsts debe ser comparable entre configuraciones.
# =============================================================================

set -euo pipefail

GEM5_BIN="${1:-${GEM5_BIN:-gem5.opt}}"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$BASE_DIR/config_multicore.py"
cd "$BASE_DIR"

NUCLEOS_LISTA=(1 2 4)
HILOS_LISTA=(1 2 4)

# Modelo de CPU para el barrido. Por defecto TIMING (TimingSimpleCPU):
# modela latencia de caché -> simTicks reales -> speedup/eficiencia válidos,
# soporta SMT y es rápido. O3 (O3CPU, fuera de orden) es el modelo "rico" del
# proyecto, PERO Gem5 v25.1 simula O3+SMT ~50x más lento (un solo config 1 núcleo
# tarda >10 min), lo hace inviable para el barrido completo. Para correr una
# config suelta en O3 (p.ej. sin SMT, multicore nativo): CPU_TYPE=O3 ./run_gem5.sh ...
CPU_TYPE="${CPU_TYPE:-TIMING}"

# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
if ! command -v "$GEM5_BIN" >/dev/null 2>&1 && [ ! -x "$GEM5_BIN" ]; then
    echo "ERROR: no se encontró Gem5 ('"$GEM5_BIN"')." >&2
    echo "  Compílalo y pásalo como primer argumento." >&2
    echo "  Ver documentacion/README.md → Instalación de Gem5." >&2
    exit 1
fi

[ -f "$CONFIG" ] || { echo "ERROR: falta $CONFIG" >&2; exit 1; }
[ -f matrices_secuencial.c ] || { echo "ERROR: falta matrices_secuencial.c" >&2; exit 1; }
[ -f matrices_paralelo.c ]   || { echo "ERROR: falta matrices_paralelo.c" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------------------
# Compilar un binario con NUM_HILOS deseado, SIN tocar el .c original
# ---------------------------------------------------------------------------
compilar_con_hilos() {
    local num_hilos="$1" destino="$2"
    if [ "$num_hilos" = "1" ]; then
        # Caso base: el #define original ya vale 1
        gcc -O2 -Wall -static -o "$destino" matrices_paralelo.c -lpthread
    else
        # Copia temporal con el #define cambiado
        sed "s/^#define NUM_HILOS .*/#define NUM_HILOS ${num_hilos}/" \
            matrices_paralelo.c > "$TMP/mp_${num_hilos}.c"
        gcc -O2 -Wall -static -o "$destino" "$TMP/mp_${num_hilos}.c" -lpthread
    fi
}

echo "==> Compilando binarios (estáticos, para modo SE)"
gcc -O2 -Wall -static -o "$TMP/matrices_secuencial" matrices_secuencial.c
echo "    secuencial OK"

# ---------------------------------------------------------------------------
# 1. Referencia secuencial (1 núcleo, sin hilos)
# ---------------------------------------------------------------------------
echo
echo "==> Secuencial de referencia (1 núcleo)"
"$GEM5_BIN" --outdir="$TMP/out" "$CONFIG" \
    --cpu-cores=1 \
    --cpu-type="$CPU_TYPE" \
    --cmd="$TMP/matrices_secuencial" \
    2>&1 | tail -8 || true

mkdir -p "$TMP/out"
if [ -s "$TMP/out/stats.txt" ]; then
    mv "$TMP/out/stats.txt" "$BASE_DIR/stats_secuencial.txt"
    echo "    -> stats_secuencial.txt"
else
    echo "    AVISO: no se generó stats.txt" >&2
fi

# ---------------------------------------------------------------------------
# 2. Barrido núcleos × hilos
# ---------------------------------------------------------------------------
for N in "${NUCLEOS_LISTA[@]}"; do
    for H in "${HILOS_LISTA[@]}"; do
        # Hilos hardware (SMT) por núcleo necesarios para que el programa
        # (main + H workers) tenga contextos suficientes. Si (H+1) <= N no
        # hace falta SMT (NT=1) y clone() reparte los workers a los núcleos
        # libres; si (H+1) > N se necesita SMT. NT = ceil((H+1)/N).
        NT=$(( (H + 1 + N - 1) / N ))
        [ "$NT" -lt 1 ] && NT=1
        echo
        echo "==> Núcleos=$N  Hilos=$H  (num-threads=$NT)"

        compilar_con_hilos "$H" "$TMP/matrices_paralelo"
        rm -rf "$TMP/out"

        "$GEM5_BIN" --outdir="$TMP/out" "$CONFIG" \
            --cpu-cores="$N" \
            --num-threads="$NT" \
            --cpu-type="$CPU_TYPE" \
            --cmd="$TMP/matrices_paralelo" \
            2>&1 | tail -8 || true

        if [ -s "$TMP/out/stats.txt" ]; then
            mv "$TMP/out/stats.txt" "$BASE_DIR/cpu${N}_${H}hilo.txt"
            echo "    -> cpu${N}_${H}hilo.txt"
        else
            echo "    AVISO: no se generó stats.txt para N=$N H=$H" >&2
        fi
    done
done

# ---------------------------------------------------------------------------
# 3. Extraer métricas y generar gráficas
# ---------------------------------------------------------------------------
echo
echo "==> Extrayendo métricas"
python3 extraer_stats.py || true

echo
echo "==> Generando gráficas"
python3 Graficas.py || true
python3 EficienciaParalela.py || true

echo
echo "Listo. Todo en: $BASE_DIR"
