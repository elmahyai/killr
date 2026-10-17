#include <float.h>
#include <limits.h>
#include <math.h>

int i1mach_(int *i) {
    switch (*i) {
    case 1:
        return 5;
    case 2:
        return 6;
    case 3:
        return 0;
    case 4:
        return 0;
    case 5:
        return 32;
    default:
        return 0;
    }
}

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
