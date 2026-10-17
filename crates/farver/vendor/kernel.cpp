#include "kernel.h"

#include "ColorSpace.h"
#include "Comparison.h"

#include <cmath>
#include <cstring>
#include <limits>
#include <type_traits>

namespace {

constexpr double NA = std::numeric_limits<double>::quiet_NaN();

constexpr int CMY = 1;
constexpr int CMYK = 2;
constexpr int HSL = 3;
constexpr int HSB = 4;
constexpr int HSV = 5;
constexpr int LAB = 6;
constexpr int HUNTERLAB = 7;
constexpr int LCH = 8;
constexpr int LUV = 9;
constexpr int RGB = 10;
constexpr int XYZ = 11;
constexpr int YXY = 12;
constexpr int HCL = 13;
constexpr int OKLAB = 14;
constexpr int OKLCH = 15;

constexpr int EUCLIDEAN = 1;
constexpr int CIE1976 = 2;
constexpr int CIE94 = 3;
constexpr int CIE2000 = 4;
constexpr int CMC = 5;

constexpr int OP_SET = 1;
constexpr int OP_ADD = 2;
constexpr int OP_MULT = 3;
constexpr int OP_LEAST = 4;
constexpr int OP_MOST = 5;

const char HEX8[] =
    "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20212223242"
    "5262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A"
    "4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F"
    "707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F90919293949"
    "5969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BA"
    "BBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE"
    "0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF";

template <typename Space>
inline int dimension() {
  return 3;
}
template <>
inline int dimension<ColorSpace::Cmyk>() {
  return 4;
}

inline int space_dim(int space) {
  return space == CMYK ? 4 : 3;
}

inline int double2int(double d) {
  d += 6755399441055744.0;
  int out = 0;
  std::memcpy(&out, &d, sizeof(out));
  return out;
}

inline int cap0255(int x) { return x < 0 ? 0 : (x > 255 ? 255 : x); }

inline double mod_val(double val, double mod, int op) {
  switch (op) {
    case OP_SET:
      return mod;
    case OP_ADD:
      return val + mod;
    case OP_MULT:
      return val * mod;
    case OP_LEAST:
      return val < mod ? mod : val;
    case OP_MOST:
      return val > mod ? mod : val;
    default:
      return val;
  }
}

inline void write_byte(char* buf, int pos, int value) {
  int num = cap0255(value) * 2;
  buf[pos] = HEX8[num];
  buf[pos + 1] = HEX8[num + 1];
}

inline void blank(char* buf) { buf[0] = '\0'; }

template <typename Space>
inline void fill_rgb(ColorSpace::Rgb* rgb, double x1, double x2, double x3,
                     double) {
  Space col(x1, x2, x3);
  col.Cap();
  col.ToRgb(rgb);
}
template <>
inline void fill_rgb<ColorSpace::Cmyk>(ColorSpace::Rgb* rgb, double x1,
                                       double x2, double x3, double x4) {
  ColorSpace::Cmyk col(x1, x2, x3, x4);
  col.Cap();
  col.ToRgb(rgb);
}

template <typename Space>
inline void grab(const Space&, double*, double*, double*, double*);

template <>
inline void grab<ColorSpace::Rgb>(const ColorSpace::Rgb& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.r;
    *x2 = color.g;
    *x3 = color.b;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Xyz>(const ColorSpace::Xyz& color, double* x1,
                                  double* x2, double* x3, double*) {
  *x1 = color.x;
  *x2 = color.y;
  *x3 = color.z;
}
template <>
inline void grab<ColorSpace::Hsl>(const ColorSpace::Hsl& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.h;
    *x2 = color.s;
    *x3 = color.l;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Lab>(const ColorSpace::Lab& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.a;
    *x3 = color.b;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Lch>(const ColorSpace::Lch& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.c;
    *x3 = color.h;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Luv>(const ColorSpace::Luv& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.u;
    *x3 = color.v;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Yxy>(const ColorSpace::Yxy& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.y1;
    *x2 = color.x;
    *x3 = color.y2;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Cmy>(const ColorSpace::Cmy& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.c;
    *x2 = color.m;
    *x3 = color.y;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Cmyk>(const ColorSpace::Cmyk& color, double* x1,
                                   double* x2, double* x3, double* x4) {
  if (color.valid) {
    *x1 = color.c;
    *x2 = color.m;
    *x3 = color.y;
    *x4 = color.k;
  } else {
    *x1 = *x2 = *x3 = *x4 = NA;
  }
}
template <>
inline void grab<ColorSpace::Hsv>(const ColorSpace::Hsv& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.h;
    *x2 = color.s;
    *x3 = color.v;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Hsb>(const ColorSpace::Hsb& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.h;
    *x2 = color.s;
    *x3 = color.b;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::HunterLab>(const ColorSpace::HunterLab& color,
                                        double* x1, double* x2, double* x3,
                                        double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.a;
    *x3 = color.b;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::Hcl>(const ColorSpace::Hcl& color, double* x1,
                                  double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.h;
    *x2 = color.c;
    *x3 = color.l;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::OkLab>(const ColorSpace::OkLab& color, double* x1,
                                    double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.a;
    *x3 = color.b;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}
template <>
inline void grab<ColorSpace::OkLch>(const ColorSpace::OkLch& color, double* x1,
                                    double* x2, double* x3, double*) {
  if (color.valid) {
    *x1 = color.l;
    *x2 = color.c;
    *x3 = color.h;
  } else {
    *x1 = *x2 = *x3 = NA;
  }
}

template <typename Space>
inline void modify_channel(Space&, double, int, int);

#define MOD3(Type, A, B, C)                                                    \
  template <>                                                                  \
  inline void modify_channel<ColorSpace::Type>(                                \
      ColorSpace::Type& color, double value, int channel, int op) {           \
    switch (channel) {                                                         \
      case 1:                                                                  \
        color.A = mod_val(color.A, value, op);                                \
        break;                                                                 \
      case 2:                                                                  \
        color.B = mod_val(color.B, value, op);                                \
        break;                                                                 \
      case 3:                                                                  \
        color.C = mod_val(color.C, value, op);                                \
        break;                                                                 \
      default:                                                                 \
        break;                                                                 \
    }                                                                          \
  }

MOD3(Rgb, r, g, b)
MOD3(Xyz, x, y, z)
MOD3(Hsl, h, s, l)
MOD3(Lab, l, a, b)
MOD3(Lch, l, c, h)
MOD3(Luv, l, u, v)
MOD3(Yxy, y1, x, y2)
MOD3(Cmy, c, m, y)
MOD3(Hsv, h, s, v)
MOD3(Hsb, h, s, b)
MOD3(HunterLab, l, a, b)
MOD3(Hcl, h, c, l)
MOD3(OkLab, l, a, b)
MOD3(OkLch, l, c, h)

template <>
inline void modify_channel<ColorSpace::Cmyk>(ColorSpace::Cmyk& color,
                                             double value, int channel,
                                             int op) {
  switch (channel) {
    case 1:
      color.c = mod_val(color.c, value, op);
      break;
    case 2:
      color.m = mod_val(color.m, value, op);
      break;
    case 3:
      color.y = mod_val(color.y, value, op);
      break;
    case 4:
      color.k = mod_val(color.k, value, op);
      break;
    default:
      break;
  }
}

template <typename Space>
inline double grab_channel(Space&, int);

#define GRABCH(Type, A, B, C)                                                  \
  template <>                                                                  \
  inline double grab_channel<ColorSpace::Type>(ColorSpace::Type& color,       \
                                               int channel) {                  \
    switch (channel) {                                                         \
      case 1:                                                                  \
        return color.A;                                                       \
      case 2:                                                                  \
        return color.B;                                                       \
      case 3:                                                                  \
        return color.C;                                                       \
      default:                                                                 \
        return 0.0;                                                           \
    }                                                                          \
  }

GRABCH(Rgb, r, g, b)
GRABCH(Xyz, x, y, z)
GRABCH(Hsl, h, s, l)
GRABCH(Lab, l, a, b)
GRABCH(Lch, l, c, h)
GRABCH(Luv, l, u, v)
GRABCH(Yxy, y1, x, y2)
GRABCH(Cmy, c, m, y)
GRABCH(Hsv, h, s, v)
GRABCH(Hsb, h, s, b)
GRABCH(HunterLab, l, a, b)
GRABCH(Hcl, h, c, l)
GRABCH(OkLab, l, a, b)
GRABCH(OkLch, l, c, h)

template <>
inline double grab_channel<ColorSpace::Cmyk>(ColorSpace::Cmyk& color,
                                             int channel) {
  switch (channel) {
    case 1:
      return color.c;
    case 2:
      return color.m;
    case 3:
      return color.y;
    case 4:
      return color.k;
    default:
      return 0.0;
  }
}

inline double colour_dist(ColorSpace::Rgb& from, ColorSpace::Rgb& to,
                          int dist) {
  switch (dist) {
    case EUCLIDEAN:
      return ColorSpace::EuclideanComparison::Compare(&from, &to);
    case CIE1976:
      return ColorSpace::Cie1976Comparison::Compare(&from, &to);
    case CIE94:
      return ColorSpace::Cie94Comparison::Compare(&from, &to);
    case CIE2000:
      return ColorSpace::Cie2000Comparison::Compare(&from, &to);
    case CMC:
      return ColorSpace::CmcComparison::Compare(&from, &to);
    default:
      return 0.0;
  }
}

template <typename From, typename To>
int convert_impl(const double* colour, int n, int ncol, double wf0, double wf1,
                 double wf2, double wt0, double wt1, double wt2, double* out,
                 int* out_ncol) {
  int need = dimension<From>();
  if (ncol < need) return need;
  int nout = dimension<To>();
  *out_ncol = nout;
  ColorSpace::Rgb rgb;
  To to{};
  double sink = 0.0;
  for (int i = 0; i < n; ++i) {
    ColorSpace::XyzConverter::SetWhiteReference(wf0, wf1, wf2);
    double x4 = need == 4 ? colour[3 * n + i] : 0.0;
    fill_rgb<From>(&rgb, colour[i], colour[n + i], colour[2 * n + i], x4);
    ColorSpace::XyzConverter::SetWhiteReference(wt0, wt1, wt2);
    ColorSpace::IConverter<To>::ToColorSpace(&rgb, &to);
    to.Cap();
    grab<To>(to, out + i, out + n + i, out + 2 * n + i,
             nout == 4 ? out + 3 * n + i : &sink);
  }
  return 0;
}

template <typename From>
int convert_to(const double* colour, int n, int ncol, int to, double wf0,
               double wf1, double wf2, double wt0, double wt1, double wt2,
               double* out, int* out_ncol) {
  switch (to) {
    case CMY:
      return convert_impl<From, ColorSpace::Cmy>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case CMYK:
      return convert_impl<From, ColorSpace::Cmyk>(colour, n, ncol, wf0, wf1,
                                                  wf2, wt0, wt1, wt2, out,
                                                  out_ncol);
    case HSL:
      return convert_impl<From, ColorSpace::Hsl>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case HSB:
      return convert_impl<From, ColorSpace::Hsb>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case HSV:
      return convert_impl<From, ColorSpace::Hsv>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case LAB:
      return convert_impl<From, ColorSpace::Lab>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case HUNTERLAB:
      return convert_impl<From, ColorSpace::HunterLab>(
          colour, n, ncol, wf0, wf1, wf2, wt0, wt1, wt2, out, out_ncol);
    case LCH:
      return convert_impl<From, ColorSpace::Lch>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case LUV:
      return convert_impl<From, ColorSpace::Luv>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case RGB:
      return convert_impl<From, ColorSpace::Rgb>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case XYZ:
      return convert_impl<From, ColorSpace::Xyz>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case YXY:
      return convert_impl<From, ColorSpace::Yxy>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case HCL:
      return convert_impl<From, ColorSpace::Hcl>(colour, n, ncol, wf0, wf1,
                                                 wf2, wt0, wt1, wt2, out,
                                                 out_ncol);
    case OKLAB:
      return convert_impl<From, ColorSpace::OkLab>(colour, n, ncol, wf0, wf1,
                                                   wf2, wt0, wt1, wt2, out,
                                                   out_ncol);
    case OKLCH:
      return convert_impl<From, ColorSpace::OkLch>(colour, n, ncol, wf0, wf1,
                                                   wf2, wt0, wt1, wt2, out,
                                                   out_ncol);
    default:
      return 0;
  }
}

/* farver's compare loop converts the `to` matrix with the `from` space. */
template <typename From, typename To>
int compare_impl(const double* from, int n, int from_ncol, const double* to,
                 int m, int to_ncol, int dist, int symmetric, double wf0,
                 double wf1, double wf2, double wt0, double wt1, double wt2,
                 double* out) {
  int from_col = dimension<From>();
  int to_col = dimension<To>();
  if (from_ncol < from_col) return from_col;
  if (to_ncol < to_col) return to_col;
  ColorSpace::Rgb from_rgb;
  ColorSpace::Rgb to_rgb;
  for (int i = 0; i < n; ++i) {
    ColorSpace::XyzConverter::SetWhiteReference(wf0, wf1, wf2);
    double fx4 = from_col == 4 ? from[3 * n + i] : 0.0;
    fill_rgb<From>(&from_rgb, from[i], from[n + i], from[2 * n + i], fx4);
    ColorSpace::XyzConverter::SetWhiteReference(wt0, wt1, wt2);
    for (int j = 0; j < m; ++j) {
      if (symmetric && j <= i) {
        out[n * j + i] = 0.0;
        continue;
      }
      double tx4 = (from_col == 4 && to_ncol >= 4) ? to[3 * m + j] : 0.0;
      fill_rgb<From>(&to_rgb, to[j], to[m + j], to[2 * m + j], tx4);
      double temp = colour_dist(from_rgb, to_rgb, dist);
      out[n * j + i] = temp < 0 ? NA : temp;
    }
  }
  return 0;
}

template <typename From>
int compare_to(const double* from, int n, int from_ncol, const double* to,
               int m, int to_ncol, int to_space, int dist, int symmetric,
               double wf0, double wf1, double wf2, double wt0, double wt1,
               double wt2, double* out) {
  switch (to_space) {
    case CMY:
      return compare_impl<From, ColorSpace::Cmy>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case CMYK:
      return compare_impl<From, ColorSpace::Cmyk>(
          from, n, from_ncol, to, m, to_ncol, dist, symmetric, wf0, wf1, wf2,
          wt0, wt1, wt2, out);
    case HSL:
      return compare_impl<From, ColorSpace::Hsl>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case HSB:
      return compare_impl<From, ColorSpace::Hsb>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case HSV:
      return compare_impl<From, ColorSpace::Hsv>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case LAB:
      return compare_impl<From, ColorSpace::Lab>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case HUNTERLAB:
      return compare_impl<From, ColorSpace::HunterLab>(
          from, n, from_ncol, to, m, to_ncol, dist, symmetric, wf0, wf1, wf2,
          wt0, wt1, wt2, out);
    case LCH:
      return compare_impl<From, ColorSpace::Lch>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case LUV:
      return compare_impl<From, ColorSpace::Luv>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case RGB:
      return compare_impl<From, ColorSpace::Rgb>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case XYZ:
      return compare_impl<From, ColorSpace::Xyz>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case YXY:
      return compare_impl<From, ColorSpace::Yxy>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case HCL:
      return compare_impl<From, ColorSpace::Hcl>(from, n, from_ncol, to, m,
                                                 to_ncol, dist, symmetric, wf0,
                                                 wf1, wf2, wt0, wt1, wt2, out);
    case OKLAB:
      return compare_impl<From, ColorSpace::OkLab>(
          from, n, from_ncol, to, m, to_ncol, dist, symmetric, wf0, wf1, wf2,
          wt0, wt1, wt2, out);
    case OKLCH:
      return compare_impl<From, ColorSpace::OkLch>(
          from, n, from_ncol, to, m, to_ncol, dist, symmetric, wf0, wf1, wf2,
          wt0, wt1, wt2, out);
    default:
      return 0;
  }
}

void put_alpha(char* buf, int alpha_value, int keep_opaque) {
  int num = cap0255(alpha_value);
  if (!keep_opaque && num == 255) {
    buf[7] = '\0';
    return;
  }
  write_byte(buf, 7, num);
  buf[9] = '\0';
}

template <typename From>
int encode_impl(const double* colour, int n, int ncol, const double* alpha,
                int alpha_len, double w0, double w1, double w2,
                char* out_bytes) {
  int need = dimension<From>();
  if (ncol < need) return need;
  ColorSpace::XyzConverter::SetWhiteReference(w0, w1, w2);
  int one_alpha = alpha_len == 1;
  char alpha1 = 'F';
  char alpha2 = 'F';
  if (alpha_len > 0) {
    double first = alpha[0];
    int first_alpha = std::isfinite(first) ? double2int(first) : 255;
    first_alpha = cap0255(first_alpha);
    alpha1 = HEX8[first_alpha * 2];
    alpha2 = HEX8[first_alpha * 2 + 1];
  }
  ColorSpace::Rgb rgb;
  for (int i = 0; i < n; ++i) {
    char* buf = out_bytes + i * 10;
    std::memcpy(buf, "#00000000", 10);
    double x4 = need == 4 ? colour[3 * n + i] : 0.0;
    fill_rgb<From>(&rgb, colour[i], colour[n + i], colour[2 * n + i], x4);
    if (!rgb.valid) {
      blank(buf);
      continue;
    }
    write_byte(buf, 1, double2int(rgb.r));
    write_byte(buf, 3, double2int(rgb.g));
    write_byte(buf, 5, double2int(rgb.b));
    if (alpha_len == 0) {
      buf[7] = '\0';
    } else if (one_alpha) {
      buf[7] = alpha1;
      buf[8] = alpha2;
      buf[9] = '\0';
    } else {
      double av = alpha[i];
      int num = std::isfinite(av) ? double2int(av) : 0;
      put_alpha(buf, num, 0);
    }
  }
  return 0;
}

int encode_rgb(const double* colour, int n, int ncol, const double* alpha,
               int alpha_len, char* out_bytes) {
  if (ncol < 3) return 3;
  int one_alpha = alpha_len == 1;
  char alpha1 = 'F';
  char alpha2 = 'F';
  if (alpha_len > 0) {
    double first = alpha[0];
    int first_alpha = std::isfinite(first) ? double2int(first) : 255;
    first_alpha = cap0255(first_alpha);
    alpha1 = HEX8[first_alpha * 2];
    alpha2 = HEX8[first_alpha * 2 + 1];
  }
  for (int i = 0; i < n; ++i) {
    char* buf = out_bytes + i * 10;
    std::memcpy(buf, "#00000000", 10);
    double r = colour[i];
    double g = colour[n + i];
    double b = colour[2 * n + i];
    if (!(std::isfinite(r) && std::isfinite(g) && std::isfinite(b))) {
      blank(buf);
      continue;
    }
    write_byte(buf, 1, double2int(r));
    write_byte(buf, 3, double2int(g));
    write_byte(buf, 5, double2int(b));
    if (alpha_len == 0) {
      buf[7] = '\0';
    } else if (one_alpha) {
      buf[7] = alpha1;
      buf[8] = alpha2;
      buf[9] = '\0';
    } else {
      double av = alpha[i];
      int num = std::isfinite(av) ? double2int(av) : 0;
      put_alpha(buf, num, 0);
    }
  }
  return 0;
}

template <typename To>
int decode_impl(const double* rgb, const double* alpha, const int* missing,
                int n, int with_alpha, double w0, double w1, double w2,
                double* out, int* out_ncol) {
  int n_channels = dimension<To>();
  int n_cols = with_alpha ? n_channels + 1 : n_channels;
  *out_ncol = n_cols;
  ColorSpace::XyzConverter::SetWhiteReference(w0, w1, w2);
  ColorSpace::Rgb src;
  To to{};
  double sink = 0.0;
  for (int i = 0; i < n; ++i) {
    if (missing[i]) {
      for (int c = 0; c < n_cols; ++c) out[c * n + i] = NA;
      continue;
    }
    src.r = rgb[i];
    src.g = rgb[n + i];
    src.b = rgb[2 * n + i];
    src.valid = true;
    ColorSpace::IConverter<To>::ToColorSpace(&src, &to);
    grab<To>(to, out + i, out + n + i, out + 2 * n + i,
             n_channels == 4 ? out + 3 * n + i : &sink);
    if (with_alpha) {
      int alpha_col = n_cols - 1;
      out[alpha_col * n + i] = alpha[i];
    }
  }
  return 0;
}

int decode_rgb(const double* rgb, const double* alpha, const int* missing,
               int n, int with_alpha, double* out, int* out_ncol) {
  int n_cols = with_alpha ? 4 : 3;
  *out_ncol = n_cols;
  for (int i = 0; i < n; ++i) {
    if (missing[i]) {
      for (int c = 0; c < n_cols; ++c) out[c * n + i] = NA;
      continue;
    }
    out[i] = rgb[i];
    out[n + i] = rgb[n + i];
    out[2 * n + i] = rgb[2 * n + i];
    if (with_alpha) out[3 * n + i] = alpha[i];
  }
  return 0;
}

void finish_hex(char* buf, const ColorSpace::Rgb& rgb, int alpha_byte) {
  if (!(std::isfinite(rgb.r) && std::isfinite(rgb.g) && std::isfinite(rgb.b))) {
    blank(buf);
    return;
  }
  write_byte(buf, 1, double2int(rgb.r));
  write_byte(buf, 3, double2int(rgb.g));
  write_byte(buf, 5, double2int(rgb.b));
  if (alpha_byte < 0) {
    buf[7] = '\0';
  } else {
    write_byte(buf, 7, alpha_byte);
    buf[9] = '\0';
  }
}

template <typename Space>
void modify_one(char* buf, int r, int g, int b, int alpha_byte, double value,
                int channel, int op, double w0, double w1, double w2) {
  std::memcpy(buf, "#00000000", 10);
  ColorSpace::XyzConverter::SetWhiteReference(w0, w1, w2);
  ColorSpace::Rgb rgb;
  rgb.r = r;
  rgb.g = g;
  rgb.b = b;
  rgb.valid = true;
  Space colour{};
  ColorSpace::IConverter<Space>::ToColorSpace(&rgb, &colour);
  modify_channel<Space>(colour, value, channel, op);
  colour.Cap();
  colour.ToRgb(&rgb);
  finish_hex(buf, rgb, alpha_byte);
}

void modify_rgb_channel(char* buf, int r, int g, int b, int alpha_byte,
                        double value, int channel, int op) {
  std::memcpy(buf, "#00000000", 10);
  int channels[3] = {r, g, b};
  int which = channel - 1;
  if (which >= 0 && which < 3) {
    double current = channels[which];
    int next = cap0255(static_cast<int>(mod_val(current, value, op)));
    channels[which] = next;
  }
  write_byte(buf, 1, channels[0]);
  write_byte(buf, 3, channels[1]);
  write_byte(buf, 5, channels[2]);
  if (alpha_byte < 0) {
    buf[7] = '\0';
  } else {
    write_byte(buf, 7, alpha_byte);
    buf[9] = '\0';
  }
}

void modify_alpha(char* buf, int r, int g, int b, int alpha_byte, double value,
                  int op) {
  std::memcpy(buf, "#00000000", 10);
  write_byte(buf, 1, r);
  write_byte(buf, 3, g);
  write_byte(buf, 5, b);
  int alpha = alpha_byte < 0 ? 255 : alpha_byte;
  alpha = double2int(mod_val(alpha / 255.0, value, op) * 255.0);
  alpha = cap0255(alpha);
  if (alpha == 255) {
    buf[7] = '\0';
  } else {
    write_byte(buf, 7, alpha);
    buf[9] = '\0';
  }
}

template <typename Space>
int modify_space(const int* r, const int* g, const int* b,
                 const int* alpha_byte, const double* value, const int* skip,
                 int n, int channel, int op, double w0, double w1, double w2,
                 char* out_bytes) {
  for (int i = 0; i < n; ++i) {
    char* buf = out_bytes + i * 10;
    if (skip[i]) {
      blank(buf);
      continue;
    }
    if (channel == 0) {
      modify_alpha(buf, r[i], g[i], b[i], alpha_byte[i], value[i], op);
    } else if (std::is_same<Space, ColorSpace::Rgb>::value) {
      modify_rgb_channel(buf, r[i], g[i], b[i], alpha_byte[i], value[i],
                         channel, op);
    } else {
      modify_one<Space>(buf, r[i], g[i], b[i], alpha_byte[i], value[i],
                        channel, op, w0, w1, w2);
    }
  }
  return 0;
}

template <typename Space>
int get_space(const int* r, const int* g, const int* b, int n, int channel,
              double w0, double w1, double w2, double* out) {
  ColorSpace::XyzConverter::SetWhiteReference(w0, w1, w2);
  for (int i = 0; i < n; ++i) {
    if (std::is_same<Space, ColorSpace::Rgb>::value) {
      ColorSpace::Rgb color(r[i], g[i], b[i]);
      out[i] = grab_channel<ColorSpace::Rgb>(color, channel);
      continue;
    }
    ColorSpace::Rgb rgb;
    rgb.r = r[i];
    rgb.g = g[i];
    rgb.b = b[i];
    rgb.valid = true;
    Space colour{};
    ColorSpace::IConverter<Space>::ToColorSpace(&rgb, &colour);
    colour.Cap();
    out[i] = grab_channel<Space>(colour, channel);
  }
  return 0;
}

}  // namespace

extern "C" int farver_convert(const double* colour, int n, int ncol, int from,
                              int to, double wf0, double wf1, double wf2,
                              double wt0, double wt1, double wt2, double* out,
                              int* out_ncol) {
  switch (from) {
    case CMY:
      return convert_to<ColorSpace::Cmy>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case CMYK:
      return convert_to<ColorSpace::Cmyk>(colour, n, ncol, to, wf0, wf1, wf2,
                                          wt0, wt1, wt2, out, out_ncol);
    case HSL:
      return convert_to<ColorSpace::Hsl>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case HSB:
      return convert_to<ColorSpace::Hsb>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case HSV:
      return convert_to<ColorSpace::Hsv>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case LAB:
      return convert_to<ColorSpace::Lab>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case HUNTERLAB:
      return convert_to<ColorSpace::HunterLab>(colour, n, ncol, to, wf0, wf1,
                                               wf2, wt0, wt1, wt2, out,
                                               out_ncol);
    case LCH:
      return convert_to<ColorSpace::Lch>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case LUV:
      return convert_to<ColorSpace::Luv>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case RGB:
      return convert_to<ColorSpace::Rgb>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case XYZ:
      return convert_to<ColorSpace::Xyz>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case YXY:
      return convert_to<ColorSpace::Yxy>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case HCL:
      return convert_to<ColorSpace::Hcl>(colour, n, ncol, to, wf0, wf1, wf2,
                                         wt0, wt1, wt2, out, out_ncol);
    case OKLAB:
      return convert_to<ColorSpace::OkLab>(colour, n, ncol, to, wf0, wf1, wf2,
                                           wt0, wt1, wt2, out, out_ncol);
    case OKLCH:
      return convert_to<ColorSpace::OkLch>(colour, n, ncol, to, wf0, wf1, wf2,
                                           wt0, wt1, wt2, out, out_ncol);
    default:
      return 0;
  }
}

extern "C" int farver_compare(const double* from, int n, int from_ncol,
                              const double* to, int m, int to_ncol,
                              int from_space, int to_space, int dist,
                              int symmetric, double wf0, double wf1, double wf2,
                              double wt0, double wt1, double wt2,
                              double lightness, double chroma, double* out) {
  ColorSpace::CmcComparison::defaultLightness = lightness;
  ColorSpace::CmcComparison::defaultChroma = chroma;
  switch (from_space) {
    case CMY:
      return compare_to<ColorSpace::Cmy>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case CMYK:
      return compare_to<ColorSpace::Cmyk>(from, n, from_ncol, to, m, to_ncol,
                                          to_space, dist, symmetric, wf0, wf1,
                                          wf2, wt0, wt1, wt2, out);
    case HSL:
      return compare_to<ColorSpace::Hsl>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case HSB:
      return compare_to<ColorSpace::Hsb>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case HSV:
      return compare_to<ColorSpace::Hsv>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case LAB:
      return compare_to<ColorSpace::Lab>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case HUNTERLAB:
      return compare_to<ColorSpace::HunterLab>(
          from, n, from_ncol, to, m, to_ncol, to_space, dist, symmetric, wf0,
          wf1, wf2, wt0, wt1, wt2, out);
    case LCH:
      return compare_to<ColorSpace::Lch>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case LUV:
      return compare_to<ColorSpace::Luv>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case RGB:
      return compare_to<ColorSpace::Rgb>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case XYZ:
      return compare_to<ColorSpace::Xyz>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case YXY:
      return compare_to<ColorSpace::Yxy>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case HCL:
      return compare_to<ColorSpace::Hcl>(from, n, from_ncol, to, m, to_ncol,
                                         to_space, dist, symmetric, wf0, wf1,
                                         wf2, wt0, wt1, wt2, out);
    case OKLAB:
      return compare_to<ColorSpace::OkLab>(from, n, from_ncol, to, m, to_ncol,
                                           to_space, dist, symmetric, wf0, wf1,
                                           wf2, wt0, wt1, wt2, out);
    case OKLCH:
      return compare_to<ColorSpace::OkLch>(from, n, from_ncol, to, m, to_ncol,
                                           to_space, dist, symmetric, wf0, wf1,
                                           wf2, wt0, wt1, wt2, out);
    default:
      return 0;
  }
}

extern "C" int farver_encode(const double* colour, int n, int ncol, int from,
                             const double* alpha, int alpha_len, double w0,
                             double w1, double w2, char* out_bytes) {
  if (from == RGB) return encode_rgb(colour, n, ncol, alpha, alpha_len, out_bytes);
  switch (from) {
    case CMY:
      return encode_impl<ColorSpace::Cmy>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case CMYK:
      return encode_impl<ColorSpace::Cmyk>(colour, n, ncol, alpha, alpha_len,
                                           w0, w1, w2, out_bytes);
    case HSL:
      return encode_impl<ColorSpace::Hsl>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case HSB:
      return encode_impl<ColorSpace::Hsb>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case HSV:
      return encode_impl<ColorSpace::Hsv>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case LAB:
      return encode_impl<ColorSpace::Lab>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case HUNTERLAB:
      return encode_impl<ColorSpace::HunterLab>(colour, n, ncol, alpha,
                                                alpha_len, w0, w1, w2,
                                                out_bytes);
    case LCH:
      return encode_impl<ColorSpace::Lch>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case LUV:
      return encode_impl<ColorSpace::Luv>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case XYZ:
      return encode_impl<ColorSpace::Xyz>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case YXY:
      return encode_impl<ColorSpace::Yxy>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case HCL:
      return encode_impl<ColorSpace::Hcl>(colour, n, ncol, alpha, alpha_len, w0,
                                          w1, w2, out_bytes);
    case OKLAB:
      return encode_impl<ColorSpace::OkLab>(colour, n, ncol, alpha, alpha_len,
                                            w0, w1, w2, out_bytes);
    case OKLCH:
      return encode_impl<ColorSpace::OkLch>(colour, n, ncol, alpha, alpha_len,
                                            w0, w1, w2, out_bytes);
    default:
      return 0;
  }
}

extern "C" int farver_decode(const double* rgb, const double* alpha,
                             const int* missing, int n, int to, int with_alpha,
                             double w0, double w1, double w2, double* out,
                             int* out_ncol) {
  if (to == RGB)
    return decode_rgb(rgb, alpha, missing, n, with_alpha, out, out_ncol);
  switch (to) {
    case CMY:
      return decode_impl<ColorSpace::Cmy>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case CMYK:
      return decode_impl<ColorSpace::Cmyk>(rgb, alpha, missing, n, with_alpha,
                                           w0, w1, w2, out, out_ncol);
    case HSL:
      return decode_impl<ColorSpace::Hsl>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case HSB:
      return decode_impl<ColorSpace::Hsb>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case HSV:
      return decode_impl<ColorSpace::Hsv>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case LAB:
      return decode_impl<ColorSpace::Lab>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case HUNTERLAB:
      return decode_impl<ColorSpace::HunterLab>(rgb, alpha, missing, n,
                                                with_alpha, w0, w1, w2, out,
                                                out_ncol);
    case LCH:
      return decode_impl<ColorSpace::Lch>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case LUV:
      return decode_impl<ColorSpace::Luv>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case XYZ:
      return decode_impl<ColorSpace::Xyz>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case YXY:
      return decode_impl<ColorSpace::Yxy>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case HCL:
      return decode_impl<ColorSpace::Hcl>(rgb, alpha, missing, n, with_alpha,
                                          w0, w1, w2, out, out_ncol);
    case OKLAB:
      return decode_impl<ColorSpace::OkLab>(rgb, alpha, missing, n, with_alpha,
                                            w0, w1, w2, out, out_ncol);
    case OKLCH:
      return decode_impl<ColorSpace::OkLch>(rgb, alpha, missing, n, with_alpha,
                                            w0, w1, w2, out, out_ncol);
    default:
      return 0;
  }
}

extern "C" int farver_modify(const int* r, const int* g, const int* b,
                             const int* alpha_byte, const double* value,
                             const int* skip, int n, int channel, int space,
                             int op, double w0, double w1, double w2,
                             char* out_bytes) {
  if (channel == 0 || space == 0) {
    return modify_space<ColorSpace::Rgb>(r, g, b, alpha_byte, value, skip, n,
                                         channel, op, w0, w1, w2, out_bytes);
  }
  switch (space) {
    case CMY:
      return modify_space<ColorSpace::Cmy>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case CMYK:
      return modify_space<ColorSpace::Cmyk>(r, g, b, alpha_byte, value, skip, n,
                                            channel, op, w0, w1, w2, out_bytes);
    case HSL:
      return modify_space<ColorSpace::Hsl>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case HSB:
      return modify_space<ColorSpace::Hsb>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case HSV:
      return modify_space<ColorSpace::Hsv>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case LAB:
      return modify_space<ColorSpace::Lab>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case HUNTERLAB:
      return modify_space<ColorSpace::HunterLab>(r, g, b, alpha_byte, value,
                                                 skip, n, channel, op, w0, w1,
                                                 w2, out_bytes);
    case LCH:
      return modify_space<ColorSpace::Lch>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case LUV:
      return modify_space<ColorSpace::Luv>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case RGB:
      return modify_space<ColorSpace::Rgb>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case XYZ:
      return modify_space<ColorSpace::Xyz>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case YXY:
      return modify_space<ColorSpace::Yxy>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case HCL:
      return modify_space<ColorSpace::Hcl>(r, g, b, alpha_byte, value, skip, n,
                                           channel, op, w0, w1, w2, out_bytes);
    case OKLAB:
      return modify_space<ColorSpace::OkLab>(r, g, b, alpha_byte, value, skip,
                                             n, channel, op, w0, w1, w2,
                                             out_bytes);
    case OKLCH:
      return modify_space<ColorSpace::OkLch>(r, g, b, alpha_byte, value, skip,
                                             n, channel, op, w0, w1, w2,
                                             out_bytes);
    default:
      return 0;
  }
}

extern "C" int farver_get_channel(const int* r, const int* g, const int* b,
                                  int n, int channel, int space, double w0,
                                  double w1, double w2, double* out) {
  switch (space) {
    case CMY:
      return get_space<ColorSpace::Cmy>(r, g, b, n, channel, w0, w1, w2, out);
    case CMYK:
      return get_space<ColorSpace::Cmyk>(r, g, b, n, channel, w0, w1, w2, out);
    case HSL:
      return get_space<ColorSpace::Hsl>(r, g, b, n, channel, w0, w1, w2, out);
    case HSB:
      return get_space<ColorSpace::Hsb>(r, g, b, n, channel, w0, w1, w2, out);
    case HSV:
      return get_space<ColorSpace::Hsv>(r, g, b, n, channel, w0, w1, w2, out);
    case LAB:
      return get_space<ColorSpace::Lab>(r, g, b, n, channel, w0, w1, w2, out);
    case HUNTERLAB:
      return get_space<ColorSpace::HunterLab>(r, g, b, n, channel, w0, w1, w2,
                                              out);
    case LCH:
      return get_space<ColorSpace::Lch>(r, g, b, n, channel, w0, w1, w2, out);
    case LUV:
      return get_space<ColorSpace::Luv>(r, g, b, n, channel, w0, w1, w2, out);
    case RGB:
      return get_space<ColorSpace::Rgb>(r, g, b, n, channel, w0, w1, w2, out);
    case XYZ:
      return get_space<ColorSpace::Xyz>(r, g, b, n, channel, w0, w1, w2, out);
    case YXY:
      return get_space<ColorSpace::Yxy>(r, g, b, n, channel, w0, w1, w2, out);
    case HCL:
      return get_space<ColorSpace::Hcl>(r, g, b, n, channel, w0, w1, w2, out);
    case OKLAB:
      return get_space<ColorSpace::OkLab>(r, g, b, n, channel, w0, w1, w2, out);
    case OKLCH:
      return get_space<ColorSpace::OkLch>(r, g, b, n, channel, w0, w1, w2, out);
    default:
      return 0;
  }
}
