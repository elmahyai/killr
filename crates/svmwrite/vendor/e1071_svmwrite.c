/* e1071 Rsvm.c svmwrite — libsvm model export without R. */

#include <stdlib.h>
#include <string.h>

#include "svm.h"

struct svm_node **sparsify(double *x, int r, int c)
{
    struct svm_node **sparse;
    int i, ii, count;

    sparse = (struct svm_node **)malloc(r * sizeof(struct svm_node *));
    for (i = 0; i < r; i++) {
        for (count = ii = 0; ii < c; ii++)
            if (x[i * c + ii] != 0)
                count++;

        sparse[i] = (struct svm_node *)malloc((count + 1) * sizeof(struct svm_node));

        for (count = ii = 0; ii < c; ii++)
            if (x[i * c + ii] != 0) {
                sparse[i][count].index = ii + 1;
                sparse[i][count].value = x[i * c + ii];
                count++;
            }

        sparse[i][count].index = -1;
    }

    return sparse;
}

struct svm_node **transsparse(double *x, int r, int *rowindex, int *colindex)
{
    struct svm_node **sparse;
    int i, ii, count = 0, nnz = 0;

    sparse = (struct svm_node **)malloc(r * sizeof(struct svm_node *));
    for (i = 0; i < r; i++) {
        nnz = rowindex[i + 1] - rowindex[i];
        sparse[i] = (struct svm_node *)malloc((nnz + 1) * sizeof(struct svm_node));

        for (ii = 0; ii < nnz; ii++) {
            sparse[i][ii].index = colindex[count];
            sparse[i][ii].value = x[count];
            count++;
        }

        sparse[i][ii].index = -1;
    }

    return sparse;
}

void e1071_svmwrite(
    double *v, int *r, int *c,
    int *rowindex,
    int *colindex,
    double *coefs,
    double *rho,
    int *compprob,
    double *probA,
    double *probB,
    int *nclasses,
    int *totnSV,
    int *labels,
    int *nSV,
    int *sparsemodel,
    int *svm_type,
    int *kernel_type,
    int *degree,
    double *gamma,
    double *coef0,
    const char *filename)
{
    struct svm_model m;
    int i;

    m.l = *totnSV;
    m.nr_class = *nclasses;
    m.sv_coef = (double **)malloc(m.nr_class * sizeof(double *));
    for (i = 0; i < m.nr_class - 1; i++) {
        m.sv_coef[i] = (double *)malloc(m.l * sizeof(double));
        memcpy(m.sv_coef[i], coefs + i * m.l, m.l * sizeof(double));
    }

    if (*sparsemodel > 0)
        m.SV = transsparse(v, *r, rowindex, colindex);
    else
        m.SV = sparsify(v, *r, *c);

    m.rho = rho;
    m.label = labels;
    m.nSV = nSV;
    if (*compprob) {
        m.probA = probA;
        m.probB = probB;
    } else {
        m.probA = NULL;
        m.probB = NULL;
    }

    m.param.svm_type = *svm_type;
    m.param.kernel_type = *kernel_type;
    m.param.degree = *degree;
    m.param.gamma = *gamma;
    m.param.coef0 = *coef0;

    m.free_sv = 1;

    svm_save_model(filename, &m);

    for (i = 0; i < m.nr_class - 1; i++)
        free(m.sv_coef[i]);
    free(m.sv_coef);

    for (i = 0; i < *r; i++)
        free(m.SV[i]);
    free(m.SV);
}
