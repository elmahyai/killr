#include <float.h>
#include <math.h>

/* SLAMCH D1MACH for IEEE double, matching gfortran libgfortran. */
double d1mach_(int *i) {
    switch (*i) {
    case 1:
        return DBL_MIN;
    case 2:
        return DBL_MAX;
    case 3:
        return pow(2.0, -53.0);
    case 4:
        return DBL_EPSILON;
    case 5:
        return log10(2.0) * 53.0;
    default:
        return 0.0;
    }
}
