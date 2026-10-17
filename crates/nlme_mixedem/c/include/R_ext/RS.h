/*
   Minimal R_ext/RS.h shim for the vendored nlme sources (see R.h).
   F77_CALL and F77_NAME use the gfortran convention: lower case, one
   trailing underscore. R_FORTRAN_NAME_SUFFIX is the default on Linux.
*/

#ifndef NLME_MIXEDEM_R_EXT_RS_H
#define NLME_MIXEDEM_R_EXT_RS_H

#include <string.h>

#define F77_NAME(x) x ## _
#define F77_CALL(x) x ## _
#define F77_SUB(x) x ## _
#define Memcpy(p1, p2, n) memcpy(p1, p2, (n) * sizeof(*(p1)))

#endif /* NLME_MIXEDEM_R_EXT_RS_H */
