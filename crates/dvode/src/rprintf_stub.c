#include <stdio.h>

void rprintf_(const char *msg) {
    if (msg) {
        fputs(msg, stderr);
    }
    fputc('\n', stderr);
}

void rprintfid_(const char *msg, int *i, double *d) {
    (void)msg;
    (void)i;
    (void)d;
}

void rprintfdi_(const char *msg, double *d, int *i) {
    (void)msg;
    (void)d;
    (void)i;
}

void rprintfdid_(const char *msg, double *d1, int *i, double *d2) {
    (void)msg;
    (void)d1;
    (void)i;
    (void)d2;
}

void rprintfd1_(const char *msg, double *d) {
    (void)msg;
    (void)d;
}

void rprintfd2_(const char *msg, double *d1, double *d2) {
    (void)msg;
    (void)d1;
    (void)d2;
}

void rprintfi1_(const char *msg, int *i) {
    (void)msg;
    (void)i;
}

void rprintfi2_(const char *msg, int *i1, int *i2) {
    (void)msg;
    (void)i1;
    (void)i2;
}

void rprintfi3_(const char *msg, int *i1, int *i2, int *i3) {
    (void)msg;
    (void)i1;
    (void)i2;
    (void)i3;
}

void rprintd1_(const char *msg, double *d) {
    (void)msg;
    (void)d;
}

void rprintd2_(const char *msg, double *d1, double *d2) {
    (void)msg;
    (void)d1;
    (void)d2;
}

void rprinti1_(const char *msg, int *i) {
    (void)msg;
    (void)i;
}
