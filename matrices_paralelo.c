#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>

#define TAM 100
#define NUM_HILOS 1

int A[TAM][TAM];
int B[TAM][TAM];
int C[TAM][TAM];

typedef struct {
    int inicio;
    int fin;
} DatosHilo;

void* multiplicar(void* arg) {

    DatosHilo* datos = (DatosHilo*) arg;

    int i, j, k;

    for(i = datos->inicio; i < datos->fin; i++) {

        for(j = 0; j < TAM; j++) {

            C[i][j] = 0;

            for(k = 0; k < TAM; k++) {

                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }

    pthread_exit(NULL);
}

int main() {

    int i, j;

    pthread_t hilos[NUM_HILOS];
    DatosHilo datos[NUM_HILOS];

    clock_t inicio, fin;
    double tiempo;

    // Inicializar matrices
    for(i = 0; i < TAM; i++) {

        for(j = 0; j < TAM; j++) {

            A[i][j] = rand() % 10;
            B[i][j] = rand() % 10;
            C[i][j] = 0;
        }
    }

    inicio = clock();

    int filasPorHilo = TAM / NUM_HILOS;

    for(i = 0; i < NUM_HILOS; i++) {

        datos[i].inicio = i * filasPorHilo;

        datos[i].fin = (i + 1) * filasPorHilo;

        pthread_create(&hilos[i], NULL, multiplicar, &datos[i]);
    }

    for(i = 0; i < NUM_HILOS; i++) {

        pthread_join(hilos[i], NULL);
    }

    fin = clock();

    tiempo = (double)(fin - inicio) / CLOCKS_PER_SEC;

    printf("Multiplicacion paralela completada\n");
    printf("Numero de hilos: %d\n", NUM_HILOS);
    printf("Tiempo de ejecucion: %f segundos\n", tiempo);

    return 0;
}
