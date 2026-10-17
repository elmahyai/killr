so <- file.path(.libPaths()[1], "units", "libs", "libudunits2.so.0")
if (file.exists(so)) dyn.load(so)
suppressPackageStartupMessages(library(sf))

bad <- st_sfc(st_point(c(0, 0)), crs = 4326)
attr(bad, "bbox") <- structure(c(xmin = -181, ymin = 0, xmax = 10, ymax = 10), class = "bbox")
good <- st_sfc(st_point(c(1, 2)), crs = 4326)
wild <- st_sfc(st_point(c(0, 0)), crs = 3857)
attr(wild, "bbox") <- structure(c(xmin = -181, ymin = 0, xmax = 10, ymax = 10), class = "bbox")
na_bb <- st_sfc(st_point(c(0, 0)), crs = 4326)
attr(na_bb, "bbox") <- structure(c(xmin = -181, ymin = NA_real_, xmax = 10, ymax = 10), class = "bbox")
empty <- st_sfc(st_point(c(0, 0)))
geom <- st_sfc(st_point(c(0, 0)), crs = 4326)
attr(geom, "bbox") <- structure(c(xmin = -181, ymin = 0, xmax = 10, ymax = 10), class = "bbox")
sf_bad <- st_sf(a = 1, geom = geom)
crsobj <- st_crs(4326)
wkt <- crsobj$wkt

token <- function(expr) {
  expr <- substitute(expr)
  warned <- character()
  val <- withCallingHandlers(eval(expr, parent.frame()), warning = function(w) {
    warned <<- c(warned, conditionMessage(w))
    invokeRestart("muffleWarning")
  })
  shown <- if (is.na(val)) "NA" else if (isTRUE(val)) "TRUE" else if (identical(val, FALSE)) "FALSE" else as.character(val)
  if (length(warned)) paste0(shown, "|", warned[[1]]) else shown
}

one <- function() {
  c(
    token(st_is_longlat(4326)),
    token(st_is_longlat(3857)),
    token(st_is_longlat(4978)),
    token(st_is_longlat(4979)),
    token(st_is_longlat(NA_real_)),
    token(st_is_longlat("+proj=longlat +datum=WGS84")),
    token(st_is_longlat("+proj=merc")),
    token(st_is_longlat("OGC:CRS84")),
    token(st_is_longlat("EPSG:4326+5703")),
    token(st_is_longlat(bad)),
    token(st_is_longlat(good)),
    token(st_is_longlat(wild)),
    token(st_is_longlat(na_bb)),
    token(st_is_longlat(empty)),
    token(st_is_longlat(sf_bad)),
    token(st_is_longlat("+proj=ob_tran +o_proj=longlat +o_lat_p=90 +o_lon_p=0")),
    token(st_is_longlat(999999)),
    token(st_is_longlat(NULL)),
    token(st_is_longlat(TRUE)),
    token(st_is_longlat(crsobj)),
    token(st_is_longlat(wkt))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", paste(value, collapse = ","), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
