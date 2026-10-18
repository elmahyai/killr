# Proof for crates/deldir, R side.
#
# Calls the .Fortran entry points that deldir() and triang.list() call
# (binsrt, master, intri) on fixed random point sets from the installed
# deldir 2.0-4. The argument lists match deldir.R, binsrt.R, and
# triang.list.R. The reference outputs are written for kernel-py.py to compare.
#
# Run from the repository root:  Rscript packages/deldir/proof/kernel-r.R

suppressPackageStartupMessages(library(deldir))

out_dir <- "packages/deldir/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

eps   <- 1e-9
sizes <- c(100L, 1000L, 3000L)
seed0 <- 20261017L
reps  <- 20L

jfmt <- function(v) sprintf("%.17g", as.double(v))
jvec <- function(v) paste0("[", paste(jfmt(v), collapse = ","), "]")
jmat <- function(m) {
    paste0("[", paste(vapply(seq_len(nrow(m)), function(r) jvec(m[r, ]), ""),
                      collapse = ","), "]")
}

# Window as deldir() builds it: data range plus 10 percent on each side.
window_of <- function(x, y) {
    xdff <- max(x) - min(x)
    ydff <- max(y) - min(y)
    c(min(x) - 0.1 * xdff, max(x) + 0.1 * xdff,
      min(y) - 0.1 * ydff, max(y) + 0.1 * ydff)
}

# binsrtR() in R/binsrt.R, call for call.
r_binsrt <- function(x, y, rw) {
    n   <- length(x)
    ind <- rep(0, n)
    .Fortran("binsrt",
             x = as.double(x),
             y = as.double(y),
             rw = as.double(rw),
             n = as.integer(n),
             ind = as.integer(ind),
             rind = as.integer(ind),
             tx = double(n),
             ty = double(n),
             ilst = integer(n),
             PACKAGE = "deldir")
}

# The master call and retry loop in deldir() (R/deldir.R). x and y are the
# bin-sorted coordinates, unpadded.
r_master <- function(x, y, rw, eps) {
    nn   <- length(x)
    ntot <- nn + 4
    x    <- c(rep(0, 4), x, rep(0, 4))
    y    <- c(rep(0, 4), y, rep(0, 4))
    ntdel <- 4 * nn
    ntdir <- 3 * nn
    madj  <- max(20, ceiling(3 * sqrt(ntot)))
    tadj  <- (madj + 1) * (ntot + 4)
    ndel  <- madj * (madj + 1) / 2
    tdel  <- 6 * ndel
    ndir  <- ndel
    tdir  <- 10 * ndir
    repeat {
        tmp <- .Fortran(
            "master",
            x = as.double(x),
            y = as.double(y),
            rw = as.double(rw),
            nn = as.integer(nn),
            ntot = as.integer(ntot),
            nadj = integer(tadj),
            madj = as.integer(madj),
            eps = as.double(eps),
            delsgs = double(tdel),
            ndel = as.integer(ndel),
            delsum = double(ntdel),
            dirsgs = double(tdir),
            ndir = as.integer(ndir),
            dirsum = double(ntdir),
            incAdj = integer(1),
            incSeg = integer(1),
            PACKAGE = "deldir"
        )
        incAdj <- tmp$incAdj
        incSeg <- tmp$incSeg
        if (incAdj == 0 & incSeg == 0) break
        if (incAdj == 1) {
            madj <- ceiling(1.2 * madj)
            tadj <- (madj + 1) * (ntot + 4)
            ndel <- max(ndel, madj * (madj + 1) / 2)
            tdel <- 6 * ndel
            ndir <- ndel
            tdir <- 10 * ndir
        }
        if (incSeg == 1) {
            ndel <- ceiling(1.2 * ndel)
            tdel <- 6 * ndel
            ndir <- ndel
            tdir <- 10 * ndir
        }
    }
    ndel_out <- tmp$ndel
    ndir_out <- tmp$ndir
    list(
        ndel = ndel_out,
        ndir = ndir_out,
        delsgs = t(matrix(tmp$delsgs, nrow = 6)[, seq_len(ndel_out), drop = FALSE]),
        delsum = matrix(tmp$delsum, ncol = 4),
        dirsgs = t(matrix(tmp$dirsgs, nrow = 10)[, seq_len(ndir_out), drop = FALSE]),
        dirsum = matrix(tmp$dirsum, ncol = 3)
    )
}

# One pass of the kernel work in deldir() and triang.list(): binsrt, master,
# and intri once per candidate triangle.
r_chain <- function(x, y, rw, tri_x, tri_y, u, v) {
    b  <- r_binsrt(x, y, rw)
    m  <- r_master(b$tx, b$ty, rw, eps)
    nt <- nrow(tri_x)
    okay <- integer(nt)
    for (i in seq_len(nt)) {
        okay[i] <- .Fortran(
            "intri",
            x = as.double(tri_x[i, ]),
            y = as.double(tri_y[i, ]),
            u = as.double(u),
            v = as.double(v),
            n = as.integer(length(u)),
            okay = integer(1),
            PACKAGE = "deldir"
        )$okay
    }
    list(binsrt = b, master = m, okay = okay)
}

results <- list()
lines   <- character(0)
for (n in sizes) {
    set.seed(seed0 + n)
    x <- runif(n, 0, 100)
    y <- runif(n, 0, 100)
    write.table(data.frame(x = sprintf("%.17g", x), y = sprintf("%.17g", y)),
                file.path(out_dir, sprintf("points-%d.csv", n)),
                sep = ",", row.names = FALSE, quote = FALSE)

    rw <- window_of(x, y)

    # Setup, untimed: the Delaunay candidate triangles, oriented as in triang.list().
    obj <- deldir::deldir(x, y, round = FALSE)
    tlist <- deldir:::prelimtlist(obj)
    xs <- obj$summary[, "x"]
    ys <- obj$summary[, "y"]
    xtri <- matrix(xs[tlist], nrow(tlist), 3)
    ytri <- matrix(ys[tlist], nrow(tlist), 3)
    ctri <- ytri - min(ys)
    dx <- cbind(xtri[, 2] - xtri[, 1], xtri[, 3] - xtri[, 2], xtri[, 1] - xtri[, 3])
    zm <- cbind(ctri[, 1] + ctri[, 2], ctri[, 2] + ctri[, 3], ctri[, 3] + ctri[, 1])
    negareas <- apply(dx * zm, 1, sum)
    clockwise <- negareas > 0
    if (any(clockwise)) {
        xc <- xtri[clockwise, , drop = FALSE]
        yc <- ytri[clockwise, , drop = FALSE]
        xtri[clockwise, ] <- xc[, c(1, 3, 2)]
        ytri[clockwise, ] <- yc[, c(1, 3, 2)]
    }
    write.table(data.frame(x1 = sprintf("%.17g", xtri[, 1]), x2 = sprintf("%.17g", xtri[, 2]),
                           x3 = sprintf("%.17g", xtri[, 3]), y1 = sprintf("%.17g", ytri[, 1]),
                           y2 = sprintf("%.17g", ytri[, 2]), y3 = sprintf("%.17g", ytri[, 3])),
                file.path(out_dir, sprintf("triangles-%d.csv", n)),
                sep = ",", row.names = FALSE, quote = FALSE)

    # One untimed run, then the median of reps timed runs (Sys.time()).
    res <- r_chain(x, y, rw, xtri, ytri, xs, ys)
    times <- numeric(reps)
    for (r in seq_len(reps)) {
        t0 <- Sys.time()
        res <- r_chain(x, y, rw, xtri, ytri, xs, ys)
        times[r] <- as.numeric(Sys.time() - t0, units = "secs") * 1000
    }
    r_ms <- median(times)

    ntri_ok <- sum(res$okay)
    tri_count <- length(triang.list(obj))
    results[[as.character(n)]] <- list(
        n = n, rw = rw, ntri = nrow(xtri), okay_count = ntri_ok,
        binsrt = res$binsrt, master = res$master, okay = res$okay, r_ms = r_ms
    )
    lines <- c(lines, sprintf(
        "n=%d ndel=%d ndir=%d candidates=%d delaunay_triangles(intri ok)=%d triang.list=%d r_median_ms=%.4f",
        n, res$master$ndel, res$master$ndir, nrow(xtri), ntri_ok, tri_count, r_ms))
}

ref_path <- file.path(out_dir, "kernel-r-reference.json")
json_cases <- vapply(results, function(cs) {
    paste0(
        "{",
        "\"n\":", cs$n,
        ",\"rw\":", jvec(cs$rw),
        ",\"ntri\":", cs$ntri,
        ",\"r_ms\":", jfmt(cs$r_ms),
        ",\"binsrt\":{",
        "\"tx\":", jvec(cs$binsrt$tx),
        ",\"ty\":", jvec(cs$binsrt$ty),
        ",\"ind\":", jvec(cs$binsrt$ind),
        ",\"rind\":", jvec(cs$binsrt$rind),
        "}",
        ",\"master\":{",
        "\"ndel\":", cs$master$ndel,
        ",\"ndir\":", cs$master$ndir,
        ",\"delsgs\":", jmat(cs$master$delsgs),
        ",\"delsum\":", jmat(cs$master$delsum),
        ",\"dirsgs\":", jmat(cs$master$dirsgs),
        ",\"dirsum\":", jmat(cs$master$dirsum),
        "}",
        ",\"okay\":", jvec(cs$okay),
        "}"
    )
}, "")
writeLines(paste0("{\"eps\":", jfmt(eps), ",\"cases\":[",
                  paste(json_cases, collapse = ","), "]}"), ref_path)

writeLines(c(
    "deldir 2.0-4 R kernels: binsrt, master, intri (.Fortran, PACKAGE=\"deldir\")",
    sprintf("deldir package version: %s", as.character(packageVersion("deldir"))),
    sprintf("eps=%g  timed runs per size=%d  timer=Sys.time()", eps, reps),
    lines
), file.path(out_dir, "kernel-r.txt"))

cat(readLines(file.path(out_dir, "kernel-r.txt")), sep = "\n")
