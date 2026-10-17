so <- file.path(.libPaths()[1], "units", "libs", "libudunits2.so.0")
if (file.exists(so)) dyn.load(so)
suppressPackageStartupMessages(library(sf))

outer <- matrix(c(0, 0, 10, 0, 10, 10, 0, 10, 0, 0), ncol = 2, byrow = TRUE)
hole <- matrix(c(1, 1, 1, 2, 2, 2, 2, 1, 1, 1), ncol = 2, byrow = TRUE)
crs4326 <- st_crs(4326)

example_sf <- st_sf(a = 1:2, geom = st_sfc(st_point(0:1), st_point(1:2)), crs = 4326)
nums <- c(xmin = 16.1, xmax = 16.6, ymax = 48.6, ymin = 47.9)
point <- st_point(c(1, 2))
pointz <- st_point(c(1, 2, 9))
pointna <- st_point(c(NA, 1))
partial <- structure(c(NA_real_, 3), class = c("XY", "POINT", "sfg"))
mp <- st_multipoint(matrix(c(1, 0, 4, 3, 2, -1), ncol = 2, byrow = TRUE))
ls <- st_linestring(matrix(c(0, 1, 5, -2, 3, 4), ncol = 2, byrow = TRUE))
poly <- st_polygon(list(outer, hole))
poly0 <- st_polygon()
polyring0 <- structure(list(matrix(numeric(0), 0, 2)), class = c("XY", "POLYGON", "sfg"))
full <- st_polygon(list(matrix(c(0, -90, 0, -90), 2, byrow = TRUE)))
mpoly <- st_multipolygon(list(list(outer, hole), list(outer + 12)))
mpoly0 <- structure(list(list(), list(outer)), class = c("XY", "MULTIPOLYGON", "sfg"))
mls <- st_multilinestring(list(outer, hole))
ls0 <- st_linestring()
mp0 <- st_multipoint()
gc <- st_geometrycollection(list(st_point(1:2), st_linestring(matrix(1:4, 2))))
gc0 <- st_geometrycollection()
gcmix <- st_geometrycollection(list(st_linestring(), st_point(c(-1, 4))))
pt_na_y <- structure(c(1, NA_real_), class = c("XY", "POINT", "sfg"))
gcinf <- st_geometrycollection(list(pt_na_y))
tri <- structure(list(outer), class = c("XY", "TRIANGLE", "sfg"))
tin <- structure(list(list(outer), list(hole)), class = c("XY", "TIN", "sfg"))
id_bb <- st_bbox(point)
bb4326 <- st_bbox(c(xmin = 1, ymin = 2, xmax = 3, ymax = 4), crs = 4326)
sfc_stored <- st_sfc(st_point(c(0, 0)), crs = 4326)
attr(sfc_stored, "bbox") <- structure(c(xmin = 9, ymin = 8, xmax = 7, ymax = 6), class = "bbox")
sf_stored <- st_sf(a = 1, geom = sfc_stored)
reorder <- c(ymax = 4, xmin = 1, junk = 9, xmax = 3, ymin = 2)
miss <- c(xmin = 1, ymin = 2)
noname <- c(1, 2, 3, 4)
dup <- c(xmin = 1, xmin = 9, ymin = 2, xmax = 3, ymax = 4)
ints <- c(xmin = 1L, ymin = 2L, xmax = 3L, ymax = 4L)
nax <- c(xmin = NA_real_, ymin = 1, xmax = 2, ymax = 3)
extra <- c(xmin = 1.5, ymin = -2, xmax = 3.25, ymax = 4, extra = 100)
nums4 <- c(xmin = 1, ymin = 2, xmax = 3, ymax = 4)
spatial <- structure(list(), class = "Spatial")
raster <- structure(list(), class = "Raster")
extent <- structure(list(), class = "Extent")
spatr <- structure(list(), class = "SpatRaster")
spatv <- structure(list(), class = "SpatVector")
spate <- structure(list(), class = "SpatExtent")
szero <- st_linestring(matrix(c(-0, 0, 0, -0), ncol = 2, byrow = TRUE))
mpna <- structure(matrix(c(NA_real_, 1, NA_real_, 2), ncol = 2, byrow = TRUE), class = c("XY", "MULTIPOINT", "sfg"))
mpnan <- structure(matrix(c(NaN, 1, NaN, 2), ncol = 2, byrow = TRUE), class = c("XY", "MULTIPOINT", "sfg"))
short <- structure(c(5), class = c("XY", "POINT", "sfg"))
msurf <- structure(list(poly), class = c("XY", "MULTISURFACE", "sfg"))
ccurve <- structure(list(st_linestring(matrix(c(0, 0, 1, 1), ncol = 2, byrow = TRUE))), class = c("XY", "COMPOUNDCURVE", "sfg"))
long <- st_linestring(cbind(1:2000, 2000:1))
zls <- st_linestring(cbind(c(1, 4), c(2, -5), c(100, -100)))
polythen <- structure(list(matrix(numeric(0), 0, 2), outer), class = c("XY", "POLYGON", "sfg"))
mpone <- st_multipoint(matrix(c(7, 8), nrow = 1))
nobbox <- st_sfc(st_point(c(1, 2)), crs = 4326)
attr(nobbox, "bbox") <- NULL
nocrs <- st_sfc(st_point(c(1, 2)))
attr(nocrs, "crs") <- NULL
sfbad <- structure(list(a = 1), class = c("sf", "data.frame"), sf_column = "geom")
sfcol <- structure(list(a = 1), class = c("sf", "data.frame"))
mat <- matrix(1:4, 2)
fac <- factor("a")
gcfull <- st_geometrycollection(list(full))
na_then <- structure(matrix(c(NA_real_, 1, 2, 3), ncol = 2, byrow = TRUE), class = c("XY", "LINESTRING", "sfg"))
circ <- st_as_sfc("CIRCULARSTRING(0 0, 1 1, 2 0)")[[1]]
circ2 <- st_as_sfc("CIRCULARSTRING(0 0, 0 1, 1 1, 1 0, 0 0)")[[1]]
circ0 <- structure(matrix(numeric(0), 0, 2), class = c("XY", "CIRCULARSTRING", "sfg"))
empty <- structure(numeric(0), names = character(0))

fmt_num <- function(z) {
  if (is.nan(z)) "NaN"
  else if (is.na(z)) "NA"
  else if (is.infinite(z)) if (z > 0) "Inf" else "-Inf"
  else sprintf("%.17g", z)
}

show_bb <- function(val) {
  if (is.list(val) && !inherits(val, "bbox")) {
    crs <- attr(val, "crs")
    crs_s <- if (is.null(crs)) "NULL" else if (is.na(crs)) "NA" else as.character(crs$input)
    return(paste0("LIST/", crs_s))
  }
  nums <- vapply(as.numeric(val), fmt_num, "")
  crs <- attr(val, "crs")
  crs_s <- if (is.null(crs)) "NULL" else if (is.na(crs)) "NA" else as.character(crs$input)
  paste0(paste(nums, collapse = ","), "/", crs_s)
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
    show_bb(val)
  }
  if (length(warned)) {
    wtxt <- vapply(warned, function(s) gsub("\n", "\\n", s, fixed = TRUE), "")
    body <- paste0(body, "|", paste(wtxt, collapse = "|"))
  }
  body
}

full_off_call <- function() {
  op <- suppressMessages(sf_use_s2(FALSE))
  on.exit(suppressMessages(sf_use_s2(op)))
  st_bbox(full)
}

one <- function() {
  paste(c(
    paste0("sf=", token(st_bbox(example_sf))),
    paste0("num=", token(st_bbox(nums, crs = crs4326))),
    paste0("point=", token(st_bbox(point))),
    paste0("pointz=", token(st_bbox(pointz))),
    paste0("pointna=", token(st_bbox(pointna))),
    paste0("partial=", token(st_bbox(partial))),
    paste0("mp=", token(st_bbox(mp))),
    paste0("ls=", token(st_bbox(ls))),
    paste0("poly=", token(st_bbox(poly))),
    paste0("poly0=", token(st_bbox(poly0))),
    paste0("polyring0=", token(st_bbox(polyring0))),
    paste0("full=", token(st_bbox(full))),
    paste0("fulloff=", token(full_off_call())),
    paste0("mpoly=", token(st_bbox(mpoly))),
    paste0("mpoly0=", token(st_bbox(mpoly0))),
    paste0("mls=", token(st_bbox(mls))),
    paste0("ls0=", token(st_bbox(ls0))),
    paste0("mp0=", token(st_bbox(mp0))),
    paste0("gc=", token(st_bbox(gc))),
    paste0("gc0=", token(st_bbox(gc0))),
    paste0("gcmix=", token(st_bbox(gcmix))),
    paste0("gcinf=", token(st_bbox(gcinf))),
    paste0("tri=", token(st_bbox(tri))),
    paste0("tin=", token(st_bbox(tin))),
    paste0("id=", token(st_bbox(id_bb))),
    paste0("idcrs=", token(st_bbox(bb4326))),
    paste0("sfc=", token(st_bbox(sfc_stored))),
    paste0("sfstore=", token(st_bbox(sf_stored))),
    paste0("reorder=", token(st_bbox(reorder))),
    paste0("miss=", token(st_bbox(miss))),
    paste0("noname=", token(st_bbox(noname))),
    paste0("dup=", token(st_bbox(dup))),
    paste0("int=", token(st_bbox(ints))),
    paste0("nax=", token(st_bbox(nax))),
    paste0("extra=", token(st_bbox(extra))),
    paste0("pos=", token(st_bbox(nums4, 4326))),
    paste0("crsna=", token(st_bbox(nums4, crs = NA))),
    paste0("chr=", token(st_bbox("nope"))),
    paste0("null=", token(st_bbox(NULL))),
    paste0("logi=", token(st_bbox(TRUE))),
    paste0("spatial=", token(st_bbox(spatial))),
    paste0("raster=", token(st_bbox(raster))),
    paste0("extent=", token(st_bbox(extent))),
    paste0("spatr=", token(st_bbox(spatr))),
    paste0("spatv=", token(st_bbox(spatv))),
    paste0("spate=", token(st_bbox(spate))),
    paste0("szero=", token(st_bbox(szero))),
    paste0("mpna=", token(st_bbox(mpna))),
    paste0("mpnan=", token(st_bbox(mpnan))),
    paste0("short=", token(st_bbox(short))),
    paste0("msurf=", token(st_bbox(msurf))),
    paste0("ccurve=", token(st_bbox(ccurve))),
    paste0("long=", token(st_bbox(long))),
    paste0("zls=", token(st_bbox(zls))),
    paste0("polythen=", token(st_bbox(polythen))),
    paste0("mpone=", token(st_bbox(mpone))),
    paste0("nobbox=", token(st_bbox(nobbox))),
    paste0("nocrs=", token(st_bbox(nocrs))),
    paste0("sfbad=", token(st_bbox(sfbad))),
    paste0("sfcol=", token(st_bbox(sfcol))),
    paste0("mat=", token(st_bbox(mat))),
    paste0("one=", token(st_bbox(1))),
    paste0("factor=", token(st_bbox(fac))),
    paste0("lst=", token(st_bbox(list(1)))),
    paste0("df=", token(st_bbox(data.frame(a = 1)))),
    paste0("gcfull=", token(st_bbox(gcfull))),
    paste0("nathen=", token(st_bbox(na_then))),
    paste0("circ=", token(st_bbox(circ))),
    paste0("circ2=", token(st_bbox(circ2))),
    paste0("circ0=", token(st_bbox(circ0))),
    paste0("empty=", token(st_bbox(empty)))
  ), collapse = ";")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
