/*
   Minimal R API shim for the vendored nlme 3.1-171 C sources.

   Declares only what src/nlmefit.c, src/matrix.c, src/pdMat.c and
   src/pythag.c use. The R session, SEXP vectors and error jumps are not
   provided by Python. Allocation maps to calloc/free, and error() jumps back
   to the entry point in src/nlme_mixedem_entry.c.

   GPL-2.0-or-later, as the nlme sources: see LICENSE.note.
*/

#ifndef NLME_MIXEDEM_R_H
#define NLME_MIXEDEM_R_H

#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <float.h>

#include "Rinternals.h"
#include "Rmath.h"
#include "R_ext/RS.h"
#include "R_ext/Arith.h"
#include "R_ext/Utils.h"
#include "R_ext/Applic.h"
#include "R_ext/Linpack.h"

void *R_chk_calloc(size_t n, size_t size);
void R_chk_free(void *p);
void error(const char *fmt, ...);
void warning(const char *fmt, ...);
int Rprintf(const char *fmt, ...);

#define R_Calloc(n, t) ((t *) R_chk_calloc((size_t) (n), sizeof(t)))
#define R_Free(p) (R_chk_free((void *) (p)), (p) = NULL)

#endif /* NLME_MIXEDEM_R_H */
