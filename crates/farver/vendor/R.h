#ifndef FARVER_STUB_R_H
#define FARVER_STUB_R_H

#include <limits.h>
#include <math.h>

#ifdef __cplusplus
#include <cmath>
inline int R_finite(double x) { return std::isfinite(x) ? 1 : 0; }
#define ISNAN(x) (std::isnan(static_cast<double>(x)) ? 1 : 0)
#else
static inline int R_finite(double x) { return isfinite(x) ? 1 : 0; }
#define ISNAN(x) (isnan(x) != 0)
#endif

/* R's NA_integer_. */
#define R_NaInt INT_MIN

#endif
