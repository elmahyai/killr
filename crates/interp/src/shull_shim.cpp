// Sweep-hull Delaunay triangulation for R package interp 1.1-6 (tri.mesh).
//
// The triangulation itself is vendor/s_hull_pro.cpp (David Sinclair, GPL3),
// compiled unchanged. This file is the post-processing from interp's
// src/shullDeltri.cpp (Albrecht Gebhardt, Roger Bivand, GPL >= 2), with the
// Rcpp and R API removed: shDt, circum, ConvexHull (Graham scan, Algoteka MIT),
// the trlist/cclist/arc/convex-hull assembly. Arithmetic, float32 storage and
// loop order are kept as in the R source so the output is the same integers.
//
// The C ABI at the bottom is an opaque handle; Rust copies the arrays out.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include "s_hull_pro.h"

namespace {

// interp's CC struct: circumcircle fields are float32.
struct CCf {
    float xc;
    float yc;
    float rc;
    float ar;
};

CCf circum(double x1, double y1, double x2, double y2, double x3, double y3) {
    CCf ret;
    double D = (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3);
    if (D == 0) {
        ret.xc = std::numeric_limits<float>::quiet_NaN();
        ret.yc = std::numeric_limits<float>::quiet_NaN();
        ret.rc = std::numeric_limits<float>::quiet_NaN();
        ret.ar = 0;
    } else {
        ret.xc =
            (((x1 - x3) * (x1 + x3) + (y1 - y3) * (y1 + y3)) / 2 * (y2 - y3) -
             ((x2 - x3) * (x2 + x3) + (y2 - y3) * (y2 + y3)) / 2 * (y1 - y3)) /
            D;
        ret.yc =
            (((x2 - x3) * (x2 + x3) + (y2 - y3) * (y2 + y3)) / 2 * (x1 - x3) -
             ((x1 - x3) * (x1 + x3) + (y1 - y3) * (y1 + y3)) / 2 * (x2 - x3)) /
            D;
        ret.rc = std::sqrt((x1 - ret.xc) * (x1 - ret.xc) + (y1 - ret.yc) * (y1 - ret.yc));
        ret.ar = std::abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0;
    }
    return ret;
}

// ---- Graham scan (convexHull.cpp), used only for the hull size ----------

struct Point2D {
    double x;
    double y;

    Point2D(double cx, double cy) {
        x = cx;
        y = cy;
    }

    Point2D operator-(Point2D r) { return {x - r.x, y - r.y}; }
    double operator*(Point2D r) { return x * r.x + y * r.y; }
    Point2D rotate90() { return {-y, x}; }
    double manhattan_length() { return std::fabs(x) + std::fabs(y); }
    bool operator==(Point2D r) { return x == r.x && y == r.y; }
    bool operator!=(Point2D r) { return x != r.x || y != r.y; }
};

std::vector<Point2D> graham_scan(std::vector<Point2D> points) {
    Point2D first_point = *std::min_element(points.begin(), points.end(), [](Point2D &left, Point2D &right) {
        return std::make_tuple(left.y, left.x) < std::make_tuple(right.y, right.x);
    });

    std::sort(points.begin(), points.end(), [&](Point2D &left, Point2D &right) {
        if (left == first_point) {
            return right != first_point;
        } else if (right == first_point) {
            return false;
        }
        double dir = (left - first_point).rotate90() * (right - first_point);
        if (dir == 0) {
            return (left - first_point).manhattan_length() < (right - first_point).manhattan_length();
        }
        return dir > 0;
    });

    std::vector<Point2D> result;
    for (auto pt : points) {
        while (result.size() >= 2 &&
               (result[result.size() - 1] - result[result.size() - 2]).rotate90() *
                       (pt - result[result.size() - 1]) <= 0) {
            result.pop_back();
        }
        result.push_back(pt);
    }
    return result;
}

// ---- shullDeltri ------------------------------------------------------------

struct Tri {
    std::vector<int> i1, i2, i3, j1, j2, j3;
    std::vector<double> xc, yc, rc, ar, rt;
    std::vector<int> ch;
    int nch = 0;
    std::vector<int> a1, a2;
    std::vector<int> k1, k2, k3;
    int na = 0;
};

}  // namespace

struct ShullResult {
    int status = 0;  // 0 ok, 1 retry with jitter (nt is -13 or -14), <0 error
    std::string error;
    int nt = 0;
    int nch = 0;
    int na = 0;
    std::vector<int> trlist;  // nt x 9, row major, 1-based indices
    std::vector<double> cclist;  // nt x 5, row major
    std::vector<int> ch;      // 1-based
    std::vector<int> a1, a2;  // 1-based, length na
};

namespace {

void run_shull(int nx, const double *xp, const double *yp, ShullResult &out) {
    std::vector<double> x(xp, xp + nx);
    std::vector<double> y(yp, yp + nx);

    // get convex hull size (ch_size for s_hull_pro)
    std::vector<Point2D> pts2;
    for (int i = 0; i < nx; i++) pts2.push_back(Point2D(x[i], y[i]));
    int CHsize = (int)graham_scan(pts2).size();

    // shDt: triangulation
    std::vector<Shx> pts;
    for (int i = 0; i < nx; i++) {
        Shx pt;
        pt.id = i;
        pt.r = x[i];
        pt.c = y[i];
        pts.push_back(pt);
    }
    std::vector<int> outx;
    int n_dups = de_duplicate(pts, outx);
    if (n_dups != 0) throw std::runtime_error("shull: duplicate points found");

    std::vector<Triad> triads;
    int ierr = s_hull_pro(pts, triads, CHsize);
    if (ierr != 1) {
        if (ierr == -1) {
            throw std::runtime_error("shull: less than 3 points, aborting");
        } else if (ierr == -2) {
            throw std::runtime_error("shull: linear structure, aborting");
        } else if (ierr == -3 || ierr == -4) {
            throw std::runtime_error("shull: cannot triangulate this set");
        } else if (ierr == -5 || ierr == -6) {
            throw std::runtime_error("shull: triangle flipping error");
        } else if (ierr == -14) {
            out.status = 1;
            out.nt = -14;
            return;
        } else if (ierr == -13) {
            out.status = 1;
            out.nt = -13;
            return;
        } else {
            throw std::runtime_error("unspecified error " + std::to_string(ierr) + " in shull!");
        }
    }

    int nT = (int)triads.size();
    Tri T;
    T.i1.resize(nT); T.i2.resize(nT); T.i3.resize(nT);
    T.j1.resize(nT); T.j2.resize(nT); T.j3.resize(nT);

    for (int i = 0; i < nT; i++) {
        // check for counter clockwise orientation (as shDt)
        double orientation = (x[triads[i].c] - x[triads[i].b]) * (y[triads[i].b] - y[triads[i].a]) +
                             (y[triads[i].c] - y[triads[i].b]) * (x[triads[i].a] - x[triads[i].b]);
        if (orientation == 0.0) {
            T.i1[i] = triads[i].a;
            T.i2[i] = triads[i].b;
            T.i3[i] = triads[i].c;
            T.j1[i] = triads[i].bc;
            T.j2[i] = triads[i].ac;
            T.j3[i] = triads[i].ab;
        }
        if (orientation < 0.0) {
            T.i1[i] = triads[i].a;
            T.i2[i] = triads[i].b;
            T.i3[i] = triads[i].c;
            T.j1[i] = triads[i].bc;
            T.j2[i] = triads[i].ac;
            T.j3[i] = triads[i].ab;
        } else {
            T.i1[i] = triads[i].a;
            T.i2[i] = triads[i].c;
            T.i3[i] = triads[i].b;
            T.j1[i] = triads[i].bc;
            T.j2[i] = triads[i].ab;
            T.j3[i] = triads[i].ac;
        }
    }

    // shullDeltri: circumcircles, inscribed radius ratio
    T.xc.assign(nT, 0.0); T.yc.assign(nT, 0.0); T.rc.assign(nT, 0.0);
    T.ar.assign(nT, 0.0); T.rt.assign(nT, 0.0);

    for (int i = 0; i < nT; i++) {
        int a = T.i1[i], b = T.i2[i], c = T.i3[i];
        CCf cc = circum(x[a], y[a], x[b], y[b], x[c], y[c]);
        double ir = cc.ar / (0.5 * (std::sqrt((x[b] - x[a]) * (x[b] - x[a]) + (y[b] - y[a]) * (y[b] - y[a])) +
                                    std::sqrt((x[c] - x[b]) * (x[c] - x[b]) + (y[c] - y[b]) * (y[c] - y[b])) +
                                    std::sqrt((x[a] - x[c]) * (x[a] - x[c]) + (y[a] - y[c]) * (y[a] - y[c]))));
        T.rt[i] = ir / cc.rc;

        // start enumeration with 1 as in R
        T.i1[i]++;
        T.i2[i]++;
        T.i3[i]++;
        T.xc[i] = cc.xc;
        T.yc[i] = cc.yc;
        T.rc[i] = cc.rc;
        T.ar[i] = cc.ar;
    }

    // convex hull arcs: neighbour triangle -1 means the arc is on the hull
    std::vector<int> cp1(nx), cp2(nx);
    int nCH = 0;
    for (int i = 0; i < nT; i++) {
        if (T.j1[i] == -1) {
            cp1[nCH] = T.i2[i];
            cp2[nCH] = T.i3[i];
            nCH++;
        }
        if (T.j2[i] == -1) {
            cp1[nCH] = T.i3[i];
            cp2[nCH] = T.i1[i];
            nCH++;
        }
        if (T.j3[i] == -1) {
            cp1[nCH] = T.i1[i];
            cp2[nCH] = T.i2[i];
            nCH++;
        }
    }

    T.ch.assign(nCH, 0);
    T.nch = nCH;
    int nArcs = (3 * nT + nCH) / 2;
    T.a1.assign(nArcs, 0);
    T.a2.assign(nArcs, 0);
    T.k1.assign(nT, 0);
    T.k2.assign(nT, 0);
    T.k3.assign(nT, 0);
    T.na = nArcs;

    // arcs, each stored once
    int ia = 0;
    for (int i = 0; i < nT; i++) {
        if (ia > nArcs) {
            throw std::runtime_error("shull: error counting arcs: " + std::to_string(ia) + " > " +
                                     std::to_string(nArcs));
        }
        bool found = false;
        for (int j = 0; j < ia; j++) {
            if ((T.a1[j] == T.i3[i] && T.a2[j] == T.i2[i]) || (T.a1[j] == T.i2[i] && T.a2[j] == T.i3[i])) {
                found = true;
                T.k1[i] = j;
                break;
            }
        }
        if (!found) {
            T.a1[ia] = T.i2[i];
            T.a2[ia] = T.i3[i];
            T.k1[i] = ia;
            ia++;
        }
        found = false;
        for (int j = 0; j < ia; j++) {
            if ((T.a1[j] == T.i1[i] && T.a2[j] == T.i3[i]) || (T.a1[j] == T.i3[i] && T.a2[j] == T.i1[i])) {
                found = true;
                T.k2[i] = j;
                break;
            }
        }
        if (!found) {
            T.a1[ia] = T.i3[i];
            T.a2[ia] = T.i1[i];
            T.k2[i] = ia;
            ia++;
        }
        found = false;
        for (int j = 0; j < ia; j++) {
            if ((T.a1[j] == T.i2[i] && T.a2[j] == T.i1[i]) || (T.a1[j] == T.i1[i] && T.a2[j] == T.i2[i])) {
                found = true;
                T.k3[i] = j;
                break;
            }
        }
        if (!found) {
            T.a1[ia] = T.i1[i];
            T.a2[ia] = T.i2[i];
            T.k3[i] = ia;
            ia++;
        }
    }

    // convex hull order: first arc, then follow the chain
    T.ch[0] = cp1[0];
    T.ch[1] = cp2[0];
    int j = 1;
    while (j < nCH - 1) {
        int found = 0;
        for (int i = 1; i < nCH; i++) {
            if (T.ch[j] == cp1[i]) {
                T.ch[j + 1] = cp2[i];
                found = 1;
            }
        }
        if (found == 0) {
            for (int i = 1; i < nCH; i++) {
                if (T.ch[j] == cp2[i]) {
                    T.ch[j + 1] = cp1[i];
                    found = 1;
                }
            }
        }
        j++;
    }

    out.status = 0;
    out.nt = nT;
    out.nch = nCH;
    out.na = nArcs;
    out.trlist.assign(static_cast<size_t>(nT) * 9, 0);
    out.cclist.assign(static_cast<size_t>(nT) * 5, 0.0);
    for (int i = 0; i < nT; i++) {
        int *row = &out.trlist[static_cast<size_t>(i) * 9];
        row[0] = T.i1[i];
        row[1] = T.i2[i];
        row[2] = T.i3[i];
        row[3] = T.j1[i] + 1;
        row[4] = T.j2[i] + 1;
        row[5] = T.j3[i] + 1;
        row[6] = T.k1[i] + 1;
        row[7] = T.k2[i] + 1;
        row[8] = T.k3[i] + 1;
        double *cc = &out.cclist[static_cast<size_t>(i) * 5];
        cc[0] = T.xc[i];
        cc[1] = T.yc[i];
        cc[2] = T.rc[i];
        cc[3] = T.ar[i];
        cc[4] = T.rt[i];
    }
    out.ch = T.ch;
    out.a1 = T.a1;  // already 1-based, as the R source stores them after the increments
    out.a2 = T.a2;
}

}  // namespace

extern "C" {

ShullResult *interp_shull_run(int n, const double *x, const double *y) {
    ShullResult *res = new ShullResult();
    try {
        run_shull(n, x, y, *res);
    } catch (const std::exception &e) {
        res->status = -100;
        res->error = e.what();
    } catch (...) {
        res->status = -100;
        res->error = "c++ exception (unknown reason)";
    }
    return res;
}

void interp_shull_free(ShullResult *r) { delete r; }

int interp_shull_status(const ShullResult *r) { return r->status; }
const char *interp_shull_error(const ShullResult *r) { return r->error.c_str(); }
int interp_shull_nt(const ShullResult *r) { return r->nt; }
int interp_shull_nch(const ShullResult *r) { return r->nch; }
int interp_shull_na(const ShullResult *r) { return r->na; }
const int *interp_shull_trlist(const ShullResult *r) { return r->trlist.data(); }
const double *interp_shull_cclist(const ShullResult *r) { return r->cclist.data(); }
const int *interp_shull_ch(const ShullResult *r) { return r->ch.data(); }
const int *interp_shull_a1(const ShullResult *r) { return r->a1.data(); }
const int *interp_shull_a2(const ShullResult *r) { return r->a2.data(); }

}  // extern "C"
