/*
   C99 hypot for the EISPACK PYTHAG routine in rs.f.

   Mirrors nlme 3.1-171 src/pythag.c (Copyright 2018 The R Core Team,
   GNU General Public License, version 2 or later; see fortran/LICENSE.note).
   The R.h dependency is dropped: the Fortran symbol is hypot_, the same
   name F77_SUB(hypot) gives under gfortran -fno-second-underscore.
*/

#include <math.h>

void hypot_(double *a, double *b, double *p)
{
    *p = hypot(*a, *b);
}
