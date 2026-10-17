/* Fortran print hooks from tseries src/formats.c, without R. */

#include <stdio.h>
#include <string.h>

void cnlprt_(char *msg, int *plen) {
    if (plen && *plen > 0) {
        char buf[1000];
        int len = *plen < (int)sizeof(buf) - 1 ? *plen : (int)sizeof(buf) - 1;
        memcpy(buf, msg, (size_t)len);
        buf[len] = '\0';
        fprintf(stderr, "\n%s\n", buf);
    }
}

void cnlprt_C(char *msg, int *plen) { cnlprt_(msg, plen); }

void h30_(void) {}
void h40_(void) {}
void h70_(void) {}
void h80_(void) {}

void h100s_(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, char *a1,
            char *a2, double *d5) {
    (void)i1;
    (void)i2;
    (void)d1;
    (void)d2;
    (void)d3;
    (void)d4;
    (void)a1;
    (void)a2;
    (void)d5;
}

void h100s_C(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, char *a1,
             char *a2, double *d5) {
    h100s_(i1, i2, d1, d2, d3, d4, a1, a2, d5);
}

void h100l_(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, char *a1,
            char *a2, double *d5, double *d6, double *d7) {
    (void)i1;
    (void)i2;
    (void)d1;
    (void)d2;
    (void)d3;
    (void)d4;
    (void)a1;
    (void)a2;
    (void)d5;
    (void)d6;
    (void)d7;
}

void h100l_C(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, char *a1,
             char *a2, double *d5, double *d6, double *d7) {
    h100l_(i1, i2, d1, d2, d3, d4, a1, a2, d5, d6, d7);
}

void h110s_(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, double *d5) {
    (void)i1;
    (void)i2;
    (void)d1;
    (void)d2;
    (void)d3;
    (void)d4;
    (void)d5;
}

void h110l_(int *i1, int *i2, double *d1, double *d2, double *d3, double *d4, double *d5,
            double *d6, double *d7) {
    (void)i1;
    (void)i2;
    (void)d1;
    (void)d2;
    (void)d3;
    (void)d4;
    (void)d5;
    (void)d6;
    (void)d7;
}

void h380_(int *i) { (void)i; }
void h400_(int *p, double *x, double *d) {
    (void)p;
    (void)x;
    (void)d;
}
void h410_(double *x) { (void)x; }
void h420_(double *x) { (void)x; }
void h450_(double *d1, double *d2, int *i1, int *i2, double *d3, double *d4) {
    (void)d1;
    (void)d2;
    (void)i1;
    (void)i2;
    (void)d3;
    (void)d4;
}
void h460_(int *i) { (void)i; }
void h470_(int *i) { (void)i; }
void h500_(int *p, double *x, double *d, double *g) {
    (void)p;
    (void)x;
    (void)d;
    (void)g;
}
