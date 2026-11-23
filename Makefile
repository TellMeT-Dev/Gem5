# =============================================================================
# Makefile — Compilación de los programas del proyecto
# =============================================================================
# Uso:
#   make              # compila normal (dinámico)
#   make estatico     # compila estático (recomendado para Gem5 modo SE)
#   make limpiar      # borra los binarios
#
# Los binarios estáticos son más robustos dentro de Gem5: no dependen del
# ld.so del host ni de rutas de librerías.
#
# Nota: TAM y NUM_HILOS siguen siendo #define en el código fuente (se mantiene
# esa decisión del proyecto); para cambiarlos hay que editar los .c y recompilar.
# =============================================================================

CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra
STATIC  ?=

BIN_SEC := matrices_secuencial
BIN_PAR := matrices_paralelo

all: $(BIN_SEC) $(BIN_PAR)

$(BIN_SEC): matrices_secuencial.c
	$(CC) $(CFLAGS) $(STATIC) -o $@ $<

$(BIN_PAR): matrices_paralelo.c
	$(CC) $(CFLAGS) $(STATIC) -o $@ $< -lpthread

# Compilación estática (para Gem5 modo SE)
estatico:
	$(MAKE) STATIC="-static" all

secuencial: $(BIN_SEC)
paralelo:   $(BIN_PAR)

limpiar:
	rm -f $(BIN_SEC) $(BIN_PAR)

.PHONY: all estatico secuencial paralelo limpiar
