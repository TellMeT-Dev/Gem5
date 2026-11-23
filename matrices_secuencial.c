#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define TAM 100

int A[TAM][TAM];
int B[TAM][TAM];
int C[TAM][TAM];

int main() {

    int i, j, k;

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

    // Multiplicación de matrices
    for(i = 0; i < TAM; i++) {
        for(j = 0; j < TAM; j++) {
            for(k = 0; k < TAM; k++) {
                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }

    fin = clock();

    tiempo = (double)(fin - inicio) / CLOCKS_PER_SEC;

    printf("Multiplicacion secuencial completada\n");
    printf("Tiempo de ejecucion: %f segundos\n", tiempo);

    return 0;
}
