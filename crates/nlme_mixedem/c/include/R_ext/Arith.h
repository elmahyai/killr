/*
   Minimal R_ext/Arith.h shim for the vendored nlme sources (see R.h).
*/

#ifndef NLME_MIXEDEM_R_EXT_ARITH_H
#define NLME_MIXEDEM_R_EXT_ARITH_H

#include <math.h>

#define R_FINITE(x) isfinite(x)

#endif /* NLME_MIXEDEM_R_EXT_ARITH_H */
