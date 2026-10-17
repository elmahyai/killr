#include <float.h>

/*
 * Netlib d1mach / i1mach. mclust's SLATEC block calls
 * d1mach(1..4) and initds calls i1mach(9) when the series length is empty.
 */
int i1mach_(int *i) {
    switch (*i) {
    case 1:
        return 5;
    case 2:
        return 6;
    case 5:
        return 32;
    case 9:
        return 2147483647;
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
        return 0x1p-53;
    case 4:
        return DBL_EPSILON;
    case 5:
        return 0.30102999566398119521;
    default:
        return 0.0;
    }
}
