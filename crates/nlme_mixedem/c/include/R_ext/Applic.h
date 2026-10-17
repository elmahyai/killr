/*
   Minimal R_ext/Applic.h shim for the vendored nlme sources (see R.h).
   Declares the optif9 interface that mixed_combined calls. optif9 is not
   reached from the mixed_EM path, and the entry point in
   src/nlme_mixedem_entry.c aborts if it is called.
*/

#ifndef NLME_MIXEDEM_R_EXT_APPLIC_H
#define NLME_MIXEDEM_R_EXT_APPLIC_H

typedef void (*fcn_p)(int, double *, double *, void *);
typedef void (*d2fcn_p)(int, double *, double **, void *);

void optif9(int nr, int n, double *x, fcn_p fcn, fcn_p d1fcn, d2fcn_p d2fcn,
	    void *state, double *typsiz, double fscale, int method, int iexp,
	    int *msg, int ndigit, int itnlim, int iagflg, int iahflg, double dlt,
	    double gradtl, double stepmx, double steptl, double *xpls,
	    double *fpls, double *gpls, int *itrmcd, double *a, double *wrk,
	    int *itncnt);

#endif /* NLME_MIXEDEM_R_EXT_APPLIC_H */
