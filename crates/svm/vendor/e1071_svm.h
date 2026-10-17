#ifndef E1071_SVM_H
#define E1071_SVM_H

#ifdef __cplusplus
extern "C" {
#endif

void e1071_svm_set_cv_seed(unsigned long seed);

void e1071_svm_train(
    double *x, int *r, int *c, double *y, int *rowindex, int *colindex, int *svm_type,
    int *kernel_type, int *degree, double *gamma, double *coef0, double *cost, double *nu,
    int *weightlabels, double *weights, int *nweights, double *cache, double *tolerance,
    double *epsilon, int *shrinking, int *cross, int *sparse, int *probability, int *nclasses,
    int *nr, int *index, int *labels, int *nSV, double *rho, double *coefs, double *sigma,
    double *probA, double *probB, double *cresults, double *ctotal1, double *ctotal2, char *error,
    int error_len);

void e1071_svm_predict(
    int decisionvalues, int probability, double *v, int *r, int *c, int *rowindex, int *colindex,
    double *coefs, double *rho, int compprob, double *probA, double *probB, int *nclasses,
    int *totnSV, int *labels, int *nSV, int *sparsemodel, int *svm_type, int *kernel_type,
    int *degree, double *gamma, double *coef0, double *x, int *xr, int *xrowindex, int *xcolindex,
    int *sparsex, double *ret, double *dec, double *prob);

#ifdef __cplusplus
}
#endif

#endif
