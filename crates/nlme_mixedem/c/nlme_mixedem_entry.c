/*
   Entry point and R API stand-ins for the vendored nlme mixed_EM.

   This file is not part of nlme. It supplies the symbols that the vendored
   src/nlmefit.c, src/matrix.c, src/pdMat.c and src/pythag.c reference, so
   that mixed_EM can be called from Rust through nlme_mixed_em(). The
   arguments of nlme_mixed_em() are the arguments of R's .C("mixed_EM")
   call in MEEM (R/lme.R), in the same order.

   R's error() longjmps out of the .C call. Here error() jumps back to
   nlme_mixed_em(), which returns 1 with the message. Memory allocated by
   R_Calloc() in the interrupted call is not freed (an error path only).

   GPL-2.0-or-later, as the nlme sources: see LICENSE.note.
*/

#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "R.h"
#include "nlmefit.h"

/* nlme.c defines sqrt_eps; matrix.c and corStruct.c read it. */
double sqrt_eps = 0.0;

static jmp_buf *nlme_jump = NULL;
static char nlme_message[512];

void *
R_chk_calloc(size_t n, size_t size)
{
    void *p = calloc(n ? n : 1, size ? size : 1);
    if (p == NULL) {
	snprintf(nlme_message, sizeof(nlme_message), "allocation failed");
	if (nlme_jump != NULL) longjmp(*nlme_jump, 1);
	abort();
    }
    return p;
}

void
R_chk_free(void *p)
{
    free(p);
}

void
error(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(nlme_message, sizeof(nlme_message), fmt, ap);
    va_end(ap);
    if (nlme_jump != NULL) longjmp(*nlme_jump, 1);
    abort();
}

void
warning(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "Warning message: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
}

int
Rprintf(const char *fmt, ...)
{
    int n;
    va_list ap;
    va_start(ap, fmt);
    n = vprintf(fmt, ap);
    va_end(ap);
    return n;
}

/* The list and vector API is used only by dimS() and getListElement(),
   which the mixed_EM path does not call. */
SEXP R_NilValue = NULL;
SEXP R_NamesSymbol = NULL;

static void
unsupported(const char *what)
{
    error("%s is not available in the nlme_mixedem crate", what);
}

SEXP Rf_getAttrib(SEXP x, SEXP name) { (void) x; (void) name; unsupported("getAttrib"); return NULL; }
int Rf_length(SEXP x) { (void) x; unsupported("length"); return 0; }
SEXP STRING_ELT(SEXP x, long i) { (void) x; (void) i; unsupported("STRING_ELT"); return NULL; }
const char *CHAR(SEXP x) { (void) x; unsupported("CHAR"); return NULL; }
SEXP VECTOR_ELT(SEXP x, long i) { (void) x; (void) i; unsupported("VECTOR_ELT"); return NULL; }
SEXP coerceVector(SEXP x, SEXPTYPE type) { (void) x; (void) type; unsupported("coerceVector"); return NULL; }
int *INTEGER(SEXP x) { (void) x; unsupported("INTEGER"); return NULL; }
SEXP Rf_protect(SEXP x) { return x; }
void Rf_unprotect(int n) { (void) n; }

/* optif9 drives mixed_combined (simulate.lme), not the EM path. */
void
optif9(int nr, int n, double *x, fcn_p fcn, fcn_p d1fcn, d2fcn_p d2fcn,
       void *state, double *typsiz, double fscale, int method, int iexp,
       int *msg, int ndigit, int itnlim, int iagflg, int iahflg, double dlt,
       double gradtl, double stepmx, double steptl, double *xpls,
       double *fpls, double *gpls, int *itrmcd, double *a, double *wrk,
       int *itncnt)
{
    (void) nr; (void) n; (void) x; (void) fcn; (void) d1fcn; (void) d2fcn;
    (void) state; (void) typsiz; (void) fscale; (void) method; (void) iexp;
    (void) msg; (void) ndigit; (void) itnlim; (void) iagflg; (void) iahflg;
    (void) dlt; (void) gradtl; (void) stepmx; (void) steptl; (void) xpls;
    (void) fpls; (void) gpls; (void) itrmcd; (void) a; (void) wrk; (void) itncnt;
    unsupported("optif9");
}

/* Returns 0 on success and 1 on an R-style error. msg receives the text. */
int
nlme_mixed_em(double *ZXy, int *pdims, double *DmHalf, int *nIter,
	      int *pdClass, int *RML, double *logLik, double *Ra,
	      double *lRSS, double *sigma, char *msg, size_t msglen)
{
    jmp_buf jump;
    jmp_buf *previous = nlme_jump;
    if (setjmp(jump)) {
	nlme_jump = previous;
	if (msg != NULL && msglen > 0) {
	    snprintf(msg, msglen, "%s", nlme_message);
	}
	return 1;
    }
    nlme_jump = &jump;
    mixed_EM(ZXy, pdims, DmHalf, nIter, pdClass, RML, logLik, Ra, lRSS, sigma);
    nlme_jump = previous;
    return 0;
}

/* mixed_loglik: the lme objective (settings[2] = 1 gives the Koshal Hessian
   path that logLik.lmeStructInt uses). logLik has room for 1 + q * (q + 1)
   values, as R allocates. Returns 0 on success, 1 on an R-style error. */
int
nlme_mixed_loglik(double *ZXy, int *pdims, double *pars, int *settings,
		  double *logLik, double *lRSS, double *sigma,
		  char *msg, size_t msglen)
{
    jmp_buf jump;
    jmp_buf *previous = nlme_jump;
    if (setjmp(jump)) {
	nlme_jump = previous;
	if (msg != NULL && msglen > 0) {
	    snprintf(msg, msglen, "%s", nlme_message);
	}
	return 1;
    }
    nlme_jump = &jump;
    mixed_loglik(ZXy, pdims, pars, settings, logLik, lRSS, sigma);
    nlme_jump = previous;
    return 0;
}

/* mixed_estimate: loglik and the estimates array dc (StrRows * ZXcols). */
int
nlme_mixed_estimate(double *ZXy, int *pdims, double *DmHalf, int *RML,
		    double *logLik, double *dc, int *invert, double *sigma,
		    char *msg, size_t msglen)
{
    jmp_buf jump;
    jmp_buf *previous = nlme_jump;
    if (setjmp(jump)) {
	nlme_jump = previous;
	if (msg != NULL && msglen > 0) {
	    snprintf(msg, msglen, "%s", nlme_message);
	}
	return 1;
    }
    nlme_jump = &jump;
    mixed_estimate(ZXy, pdims, DmHalf, RML, logLik, dc, invert, sigma);
    nlme_jump = previous;
    return 0;
}

/* mixed_decomp: rewrites ZXy in place with the decomposition (R's .C). */
int
nlme_mixed_decomp(double *ZXy, int *pdims, char *msg, size_t msglen)
{
    jmp_buf jump;
    jmp_buf *previous = nlme_jump;
    if (setjmp(jump)) {
	nlme_jump = previous;
	if (msg != NULL && msglen > 0) {
	    snprintf(msg, msglen, "%s", nlme_message);
	}
	return 1;
    }
    nlme_jump = &jump;
    mixed_decomp(ZXy, pdims);
    nlme_jump = previous;
    return 0;
}

