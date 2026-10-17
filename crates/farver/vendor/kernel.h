#ifndef FARVER_KERNEL_H
#define FARVER_KERNEL_H

/* Colour-space ids match farver's R vector, one-based.
   Return 0 on success. A positive return is the column count the
   colour space required when the input was short. */

#ifdef __cplusplus
extern "C" {
#endif

int farver_convert(const double* colour, int n, int ncol, int from, int to,
                   double wf0, double wf1, double wf2, double wt0, double wt1,
                   double wt2, double* out, int* out_ncol);

int farver_compare(const double* from, int n, int from_ncol, const double* to,
                   int m, int to_ncol, int from_space, int to_space, int dist,
                   int symmetric, double wf0, double wf1, double wf2,
                   double wt0, double wt1, double wt2, double lightness,
                   double chroma, double* out);

/* alpha_len 0: no alpha. 1: one alpha for every row. n: one per row.
   alpha values are already scaled by 255. out_bytes is n blocks of 10
   bytes; an empty string is a missing colour. */
int farver_encode(const double* colour, int n, int ncol, int from,
                  const double* alpha, int alpha_len, double w0, double w1,
                  double w2, char* out_bytes);

/* rgb is n by 3, column major, channels in 0..255. alpha is length n
   on 0..1. missing[i] writes NA across the row. */
int farver_decode(const double* rgb, const double* alpha, const int* missing,
                  int n, int to, int with_alpha, double w0, double w1,
                  double w2, double* out, int* out_ncol);

/* alpha_byte[i] < 0 omits the alpha digits. skip[i] writes a missing
   colour. channel 0 modifies alpha; otherwise channel is 1..4. */
int farver_modify(const int* r, const int* g, const int* b,
                  const int* alpha_byte, const double* value, const int* skip,
                  int n, int channel, int space, int op, double w0, double w1,
                  double w2, char* out_bytes);

int farver_get_channel(const int* r, const int* g, const int* b, int n,
                       int channel, int space, double w0, double w1, double w2,
                       double* out);

#ifdef __cplusplus
}
#endif

#endif
