#include <Rinternals.h>
#include <R_ext/Rdynload.h>

extern int n_eq;
extern int histsize, offset, indexhist, starthist, endreached, initialisehist;
extern int interpolMethod;
extern double *histtime, *histvar, *histdvar;

SEXP dump_lag_history(void) {
  int i, n;
  SEXP out, tn, vn, dn, dims, names;
  if (initialisehist == 0)
    error("history not initialised");
  n = histsize;
  PROTECT(out = allocVector(VECSXP, 10));
  PROTECT(tn = allocVector(REALSXP, n));
  for (i = 0; i < n; i++)
    REAL(tn)[i] = histtime[i];
  SET_VECTOR_ELT(out, 0, tn);

  PROTECT(vn = allocVector(REALSXP, (R_xlen_t)offset * (R_xlen_t)n));
  for (i = 0; i < offset * n; i++)
    REAL(vn)[i] = histvar[i];
  SET_VECTOR_ELT(out, 1, vn);

  PROTECT(dn = allocVector(REALSXP, (R_xlen_t)n_eq * (R_xlen_t)n));
  for (i = 0; i < n_eq * n; i++)
    REAL(dn)[i] = histdvar[i];
  SET_VECTOR_ELT(out, 2, dn);

  SET_VECTOR_ELT(out, 3, ScalarInteger(n_eq));
  SET_VECTOR_ELT(out, 4, ScalarInteger(histsize));
  SET_VECTOR_ELT(out, 5, ScalarInteger(indexhist));
  SET_VECTOR_ELT(out, 6, ScalarInteger(starthist));
  SET_VECTOR_ELT(out, 7, ScalarInteger(endreached));
  SET_VECTOR_ELT(out, 8, ScalarInteger(offset));
  SET_VECTOR_ELT(out, 9, ScalarInteger(interpolMethod));

  PROTECT(names = allocVector(STRSXP, 10));
  SET_STRING_ELT(names, 0, mkChar("histtime"));
  SET_STRING_ELT(names, 1, mkChar("histvar"));
  SET_STRING_ELT(names, 2, mkChar("histdvar"));
  SET_STRING_ELT(names, 3, mkChar("n_eq"));
  SET_STRING_ELT(names, 4, mkChar("histsize"));
  SET_STRING_ELT(names, 5, mkChar("indexhist"));
  SET_STRING_ELT(names, 6, mkChar("starthist"));
  SET_STRING_ELT(names, 7, mkChar("endreached"));
  SET_STRING_ELT(names, 8, mkChar("offset"));
  SET_STRING_ELT(names, 9, mkChar("interpolMethod"));
  setAttrib(out, R_NamesSymbol, names);

  UNPROTECT(5);
  return out;
}

static const R_CallMethodDef CallEntries[] = {
    {"dump_lag_history", (DL_FUNC)&dump_lag_history, 0},
    {NULL, NULL, 0}};

void R_init_lagvalue_dump(DllInfo *dll) {
  R_registerRoutines(dll, NULL, CallEntries, NULL, NULL);
  R_useDynamicSymbols(dll, FALSE);
}
