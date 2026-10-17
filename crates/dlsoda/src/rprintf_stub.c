#include <stdio.h>

void rprintf_(const char *msg) {
    if (msg) {
        fputs(msg, stderr);
    }
    fputc('\n', stderr);
}

void rprintfi1_(const char *msg, int *i1) {
    (void)msg;
    (void)i1;
}

void rprintfi2_(const char *msg, int *i1, int *i2) {
    (void)msg;
    (void)i1;
    (void)i2;
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

void rexit_(const char *msg) {
    (void)msg;
}

void dblepr_(const char *msg, int *len, double *vals, int *n) {
    (void)msg;
    (void)len;
    (void)vals;
    (void)n;
}

void intpr_(const char *msg, int *len, int *vals, int *n) {
    (void)msg;
    (void)len;
    (void)vals;
    (void)n;
}
