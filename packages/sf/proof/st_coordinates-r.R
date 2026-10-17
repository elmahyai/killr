so <- file.path(.libPaths()[1], "units", "libs", "libudunits2.so.0")
if (file.exists(so)) dyn.load(so)
suppressPackageStartupMessages(library(sf))
stopifnot(packageDescription("sf")$Version == "1.1-3")

outer <- matrix(c(0, 0, 10, 0, 10, 10, 0, 10, 0, 0), ncol = 2, byrow = TRUE)
hole <- matrix(c(1, 1, 1, 2, 2, 2, 2, 1, 1, 1), ncol = 2, byrow = TRUE)
outer12 <- outer + 12

pt <- function(x, dim = "XY") structure(x, class = c(dim, "POINT", "sfg"))
ln <- function(m, dim = "XY") structure(m, class = c(dim, "LINESTRING", "sfg"))
mp <- function(m, dim = "XY") structure(m, class = c(dim, "MULTIPOINT", "sfg"))
poly <- function(rings, dim = "XY") structure(rings, class = c(dim, "POLYGON", "sfg"))
mls <- function(parts, dim = "XY") structure(parts, class = c(dim, "MULTILINESTRING", "sfg"))
mpoly <- function(parts, dim = "XY") structure(parts, class = c(dim, "MULTIPOLYGON", "sfg"))
as_sfc <- function(kind, geoms, precision = 0) {
  structure(geoms, class = c(paste0("sfc_", kind), "sfc"), precision = precision)
}
as_sf <- function(geom) structure(list(geom = geom), class = c("sf", "data.frame"), sf_column = "geom")

named <- structure(c(a = 1, b = 2), class = c("XY", "POINT", "sfg"))
zring <- cbind(outer, 1:5)
suite <- matrix(c(
  0.5, -0.5,
  1.5, -1.5,
  2.5, -2.5,
  1.25, -1.25,
  1.35, -1.35,
  0.05, -0.05,
  1.23456789, -1.23456789,
  0.04, -0.04,
  -0, 0,
  NA_real_, NaN,
  Inf, -Inf
), ncol = 2, byrow = TRUE)
special <- pt(c(-0, NA_real_, NaN, Inf), "XYZM")
long <- ln(cbind(1:2000, 2000:1))
int_line <- ln(matrix(1:6, ncol = 2))
prec10 <- as_sfc("POINT", list(pt(c(1.234, 1.234))), precision = 10)
prec_na <- as_sfc("POINT", list(pt(c(1.25, -1.25))))
attr(prec_na, "precision") <- NA_real_
prec_null <- structure(list(pt(c(1.25, -1.25))), class = c("sfc_POINT", "sfc"))
bad_mp <- mpoly(list(list(), list(outer)))
unequal <- as_sfc("POINT", list(pt(c(1, 2)), pt(c(3, 4, 5), "XYZ")))
short <- as_sfc("POINT", list(pt(5)))
zero_pt <- as_sfc("POINT", list(structure(numeric(0), class = c("XY", "POINT", "sfg"))))

obj_pts <- as_sfc("POINT", list(pt(c(1.234, 5)), pt(c(-2, 0))))
obj_ints <- as_sfc("POINT", list(pt(1:2), pt(3:4)))
obj_named <- as_sfc("POINT", list(named))
obj_z <- as_sfc("POINT", list(pt(c(1, 2, 9), "XYZ")))
obj_m <- as_sfc("POINT", list(pt(c(1, 2, 9), "XYM")))
obj_zm <- as_sfc("POINT", list(pt(c(1, 2, 3, 4), "XYZM")))
obj_na <- as_sfc("POINT", list(pt(c(NA_real_, 1))))
obj_nan <- as_sfc("POINT", list(pt(c(NaN, 1))))
obj_neg0 <- as_sfc("POINT", list(pt(c(-0, 0))))
obj_emptypt <- st_sfc(st_point())
obj_lines <- as_sfc("LINESTRING", list(ln(outer), ln(hole)))
obj_emptyline <- st_sfc(st_linestring(), ln(matrix(c(1, 2, 3, 4), ncol = 2, byrow = TRUE)))
obj_twoline0 <- st_sfc(st_linestring(), st_linestring())
obj_mp <- as_sfc("MULTIPOINT", list(
  mp(matrix(c(1, 0, 4, 3, 2, -1), ncol = 2, byrow = TRUE)),
  mp(matrix(c(7, 8), nrow = 1))
))
obj_poly <- as_sfc("POLYGON", list(poly(list(outer, hole))))
obj_twopoly <- as_sfc("POLYGON", list(poly(list(outer)), poly(list(hole))))
obj_polyz <- as_sfc("POLYGON", list(poly(list(zring), "XYZ")))
obj_poly0 <- st_sfc(st_polygon(), st_polygon())
obj_ring0 <- as_sfc("POLYGON", list(poly(list(matrix(numeric(0), 0, 2)))))
obj_ringthen <- as_sfc("POLYGON", list(poly(list(matrix(numeric(0), 0, 2), outer))))
obj_mpoly <- as_sfc("MULTIPOLYGON", list(mpoly(list(list(outer, hole), list(outer12)))))
obj_twompoly <- st_sfc(st_multipolygon(list(list(outer))), st_multipolygon(list(list(hole))))
obj_mpoly0 <- st_sfc(st_multipolygon(), st_multipolygon())
obj_mls <- as_sfc("MULTILINESTRING", list(mls(list(outer, hole))))
obj_mls0 <- st_sfc(st_multilinestring())
obj_zline <- as_sfc("LINESTRING", list(ln(cbind(c(1, 4), c(2, -5), c(100, -100)), "XYZ")))
obj_xym <- as_sfc("MULTIPOINT", list(mp(cbind(c(1, 4), c(2, -5), c(7, 8)), "XYM")))
obj_intline <- as_sfc("LINESTRING", list(int_line))
obj_intround <- as_sfc("LINESTRING", list(int_line), precision = 10)
obj_sfg <- pt(c(1, 2))
obj_sfground <- ln(matrix(c(1.234, 1.234), nrow = 1))
obj_sf <- as_sf(as_sfc("POINT", list(pt(0:1), pt(1:2))))
obj_sfround <- as_sf(prec10)
obj_empty <- st_sfc()
obj_plain <- as_sfc("POINT", list(pt(c(1.234, 1.234))))
obj_r100 <- as_sfc("POINT", list(pt(c(1.234, 1.234))), precision = 100)
obj_s10 <- as_sfc("LINESTRING", list(ln(suite)), precision = 10)
obj_s100 <- as_sfc("LINESTRING", list(ln(suite)), precision = 100)
obj_s01 <- as_sfc("LINESTRING", list(ln(suite)), precision = 0.1)
obj_sneg <- as_sfc("LINESTRING", list(ln(suite)), precision = -1)
obj_sp10 <- as_sfc("POINT", list(special), precision = 10)
obj_spneg <- as_sfc("POINT", list(special), precision = -1)
obj_long <- as_sfc("LINESTRING", list(long))
obj_gc <- st_sfc(st_geometrycollection(list(pt(1:2))))
obj_mixed <- st_sfc(pt(1:2), ln(matrix(1:4, ncol = 2)))
obj_tri <- as_sfc("TRIANGLE", list(structure(list(outer), class = c("XY", "TRIANGLE", "sfg"))))
obj_bad <- structure(list(a = 1), class = c("sf", "data.frame"), sf_column = "geom")
obj_nocol <- structure(list(a = 1), class = c("sf", "data.frame"))

fmt_num <- function(z) {
  if (is.nan(z)) return("NaN")
  if (is.na(z)) return("NA")
  if (is.infinite(z)) return(if (z > 0) "Inf" else "-Inf")
  if (z == 0 && (1 / z) < 0) return("-0")
  sprintf("%.17g", z)
}

show_mat <- function(val) {
  cn <- colnames(val)
  cn_s <- if (is.null(cn)) "" else paste(cn, collapse = "|")
  nums <- if (length(val) == 0) "" else paste(vapply(as.numeric(val), fmt_num, ""), collapse = ",")
  paste0(typeof(val), "/", nrow(val), "x", ncol(val), "/", cn_s, "/", nums)
}

token <- function(expr) {
  expr <- substitute(expr)
  warned <- character()
  val <- tryCatch(
    withCallingHandlers(
      eval(expr, parent.frame()),
      warning = function(w) {
        warned <<- c(warned, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) structure(conditionMessage(e), class = "errtok")
  )
  body <- if (inherits(val, "errtok")) {
    paste0("ERR ", gsub("\n", "\\n", as.character(val), fixed = TRUE))
  } else {
    show_mat(val)
  }
  if (length(warned)) {
    wtxt <- vapply(warned, function(s) gsub("\n", "\\n", s, fixed = TRUE), "")
    body <- paste0(body, "|", paste(wtxt, collapse = "|"))
  }
  body
}

obj_badmp <- as_sfc("MULTIPOLYGON", list(bad_mp))

one <- function() {
  paste(c(
    paste0("pts=", token(st_coordinates(obj_pts))),
    paste0("ints=", token(st_coordinates(obj_ints))),
    paste0("named=", token(st_coordinates(obj_named))),
    paste0("z=", token(st_coordinates(obj_z))),
    paste0("m=", token(st_coordinates(obj_m))),
    paste0("zm=", token(st_coordinates(obj_zm))),
    paste0("na=", token(st_coordinates(obj_na))),
    paste0("nan=", token(st_coordinates(obj_nan))),
    paste0("neg0=", token(st_coordinates(obj_neg0))),
    paste0("emptypt=", token(st_coordinates(obj_emptypt))),
    paste0("lines=", token(st_coordinates(obj_lines))),
    paste0("emptyline=", token(st_coordinates(obj_emptyline))),
    paste0("twoline0=", token(st_coordinates(obj_twoline0))),
    paste0("mp=", token(st_coordinates(obj_mp))),
    paste0("poly=", token(st_coordinates(obj_poly))),
    paste0("twopoly=", token(st_coordinates(obj_twopoly))),
    paste0("polyz=", token(st_coordinates(obj_polyz))),
    paste0("poly0=", token(st_coordinates(obj_poly0))),
    paste0("ring0=", token(st_coordinates(obj_ring0))),
    paste0("ringthen=", token(st_coordinates(obj_ringthen))),
    paste0("mpoly=", token(st_coordinates(obj_mpoly))),
    paste0("twompoly=", token(st_coordinates(obj_twompoly))),
    paste0("mpoly0=", token(st_coordinates(obj_mpoly0))),
    paste0("mls=", token(st_coordinates(obj_mls))),
    paste0("mls0=", token(st_coordinates(obj_mls0))),
    paste0("zline=", token(st_coordinates(obj_zline))),
    paste0("xym=", token(st_coordinates(obj_xym))),
    paste0("intline=", token(st_coordinates(obj_intline))),
    paste0("intround=", token(st_coordinates(obj_intround, round = TRUE))),
    paste0("sfg=", token(st_coordinates(obj_sfg))),
    paste0("sfground=", token(st_coordinates(obj_sfground, round = TRUE))),
    paste0("sf=", token(st_coordinates(obj_sf))),
    paste0("sfround=", token(st_coordinates(obj_sfround, round = TRUE))),
    paste0("empty=", token(st_coordinates(obj_empty))),
    paste0("plain=", token(st_coordinates(obj_plain))),
    paste0("r10=", token(st_coordinates(prec10, round = TRUE))),
    paste0("rfalse=", token(st_coordinates(prec10, round = FALSE))),
    paste0("r100=", token(st_coordinates(obj_r100, round = TRUE))),
    paste0("r0=", token(st_coordinates(prec10, round = 0))),
    paste0("r2=", token(st_coordinates(prec10, round = 2))),
    paste0("pos=", token(st_coordinates(prec10, TRUE))),
    paste0("s10=", token(st_coordinates(obj_s10, round = TRUE))),
    paste0("s100=", token(st_coordinates(obj_s100, round = TRUE))),
    paste0("s01=", token(st_coordinates(obj_s01, round = TRUE))),
    paste0("sneg=", token(st_coordinates(obj_sneg, round = TRUE))),
    paste0("sp10=", token(st_coordinates(obj_sp10, round = TRUE))),
    paste0("spneg=", token(st_coordinates(obj_spneg, round = TRUE))),
    paste0("long=", token(st_coordinates(obj_long))),
    paste0("gc=", token(st_coordinates(obj_gc))),
    paste0("mixed=", token(st_coordinates(obj_mixed))),
    paste0("tri=", token(st_coordinates(obj_tri))),
    paste0("bad=", token(st_coordinates(obj_bad))),
    paste0("nocol=", token(st_coordinates(obj_nocol))),
    paste0("null=", token(st_coordinates(NULL))),
    paste0("dbl=", token(st_coordinates(1.5))),
    paste0("chr=", token(st_coordinates("a"))),
    paste0("logi=", token(st_coordinates(TRUE))),
    paste0("lst=", token(st_coordinates(list(1)))),
    paste0("badmp=", token(st_coordinates(obj_badmp))),
    paste0("unequal=", token(st_coordinates(unequal))),
    paste0("short=", token(st_coordinates(short))),
    paste0("zeropt=", token(st_coordinates(zero_pt))),
    paste0("naprec=", token(st_coordinates(prec_na, round = TRUE))),
    paste0("nullprec=", token(st_coordinates(prec_null, round = TRUE))),
    paste0("rvec=", token(st_coordinates(prec10, round = c(TRUE, FALSE)))),
    paste0("rna=", token(st_coordinates(prec10, round = NA))),
    paste0("rstr=", token(st_coordinates(prec10, round = "TRUE")))
  ), collapse = ";")
}

ex <- st_sfc(st_point(c(1.234, 1.234)), crs = 3003)
m1 <- st_coordinates(ex)
st_precision(ex) <- 1e1
m2 <- st_coordinates(ex, round = TRUE)
st_precision(ex) <- units::set_units(1, cm)
m3 <- st_coordinates(ex, round = TRUE)
cell <- function(m) paste(paste0(colnames(m), " ", vapply(m[1, ], fmt_num, "")), collapse = " ")
example <- c(
  paste0("st_coordinates(x) returns ", cell(m1), "."),
  paste0("st_coordinates(x, round = TRUE) with precision 10 returns ", cell(m2), "."),
  paste0("st_coordinates(x, round = TRUE) after units::set_units(1, cm) returns ", cell(m3), ".")
)
out <- "/home/ahmed/killr_projects/killr/packages/sf/docs/output/st_coordinates-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(example, out)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
