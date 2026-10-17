so <- file.path(.libPaths()[1], "units", "libs", "libudunits2.so.0")
if (file.exists(so)) dyn.load(so)
suppressPackageStartupMessages(library(sf))

esc <- function(s) {
  if (is.null(s) || length(s) != 1 || is.na(s)) return("NA")
  s <- gsub("\\", "\001", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  s <- gsub("\x1f", "\\x1f", s, fixed = TRUE)
  s <- gsub("\x1e", "\\x1e", s, fixed = TRUE)
  s <- gsub("\001", "\\\\", s, fixed = TRUE)
  s
}

fld_num <- function(v) if (length(v) != 1 || is.na(v)) "NA" else sprintf("%.17g", as.numeric(v))
fld_chr <- function(v) if (length(v) != 1 || is.na(v)) "NA" else esc(v)
fld_log <- function(v) if (length(v) != 1 || is.na(v)) "NA" else if (isTRUE(v)) "TRUE" else "FALSE"
fld_int <- function(v) if (length(v) != 1 || is.na(v)) "NA" else as.character(v)

ser_par <- function(p) {
  axn <- paste(ifelse(is.na(p$axes$name), "NA", p$axes$name), collapse = "|")
  axo <- paste(ifelse(is.na(p$axes$orientation), "NA", as.character(p$axes$orientation)), collapse = "|")
  fields <- c(
    paste0("SemiMajor=", fld_num(p$SemiMajor)),
    paste0("SemiMinor=", fld_num(p$SemiMinor)),
    paste0("InvFlattening=", fld_num(p$InvFlattening)),
    paste0("IsGeographic=", fld_log(p$IsGeographic)),
    paste0("units_gdal=", fld_chr(p$units_gdal)),
    paste0("IsVertical=", fld_log(p$IsVertical)),
    paste0("WktPretty=", fld_chr(p$WktPretty)),
    paste0("Wkt=", fld_chr(p$Wkt)),
    paste0("Name=", fld_chr(p$Name)),
    paste0("proj4string=", fld_chr(p$proj4string)),
    paste0("epsg=", fld_int(p$epsg)),
    paste0("yx=", fld_log(p$yx)),
    paste0("ProjJson=", fld_chr(p$ProjJson)),
    paste0("WKT1_ESRI=", fld_chr(p$WKT1_ESRI)),
    paste0("srid=", fld_chr(p$srid)),
    paste0("axes_name=", esc(axn)),
    paste0("axes_orientation=", axo),
    paste0("gcs_crs=", fld_chr(p$gcs_crs)),
    paste0("is_geocentric=", fld_log(p$is_geocentric))
  )
  paste(c("PAR", fields), collapse = "\x1f")
}

ser_val <- function(val) {
  if (inherits(val, "probe_err")) return(paste0("ERR", "\x1f", esc(as.character(val))))
  if (is.null(val)) return("NULL")
  if (inherits(val, "crs")) {
    if (is.na(val)) return("NACRS")
    inp <- val$input
    wkt <- val$wkt
    return(paste("CRS", if (is.na(inp)) "NA" else esc(inp), if (is.na(wkt)) "NA" else esc(wkt), sep = "\x1f"))
  }
  if (inherits(val, "crs_parameters")) return(ser_par(val))
  if (is.list(val) && length(val) == 0) return("LIST")
  if (is.character(val)) return(paste0("CHR", "\x1f", if (length(val) != 1 || is.na(val)) "NA" else esc(val)))
  if (is.integer(val)) return(paste0("INT", "\x1f", fld_int(val)))
  if (is.logical(val)) return(fld_log(val))
  if (is.numeric(val)) return(paste0("DBL", "\x1f", fld_num(val)))
  paste0("OTHER", "\x1f", esc(paste(capture.output(str(val)), collapse = " ")))
}

token <- function(label, expr) {
  expr <- substitute(expr)
  warned <- character()
  messaged <- character()
  val <- tryCatch(
    withCallingHandlers(
      eval(expr, parent.frame()),
      warning = function(w) {
        warned <<- c(warned, sub("[\r\n]+$", "", conditionMessage(w)))
        invokeRestart("muffleWarning")
      },
      message = function(m) {
        messaged <<- c(messaged, sub("[\r\n]+$", "", conditionMessage(m)))
        invokeRestart("muffleMessage")
      }
    ),
    error = function(e) structure(conditionMessage(e), class = "probe_err")
  )
  body <- ser_val(val)
  if (length(warned))
    body <- paste(body, paste0("W:", paste(vapply(warned, esc, ""), collapse = "\x1e")), sep = "\x1f")
  if (length(messaged))
    body <- paste(body, paste0("M:", paste(vapply(messaged, esc, ""), collapse = "\x1e")), sep = "\x1f")
  paste(label, body, sep = "\x1f")
}

crs4326 <- st_crs(4326)
merc <- st_crs("+proj=merc")
sfc4326 <- st_sfc(st_point(c(0, 0)), crs = 4326)
sf4326 <- st_sf(a = 1, geom = sfc4326)
bb <- st_bbox(sfc4326)
bb0 <- structure(c(xmin = 0, ymin = 0, xmax = 1, ymax = 1), class = "bbox")
old_sfc <- st_sfc(st_point(c(1, 1)), crs = 4326)
attr(old_sfc, "crs") <- structure(list(epsg = 4326, proj4string = "+proj=longlat"), class = "crs")
old_na <- st_sfc(st_point(c(1, 1)), crs = 4326)
attr(old_na, "crs") <- structure(list(epsg = NA_real_, proj4string = "+proj=longlat"), class = "crs")
null_sfc <- st_sfc(st_point(c(0, 0)), crs = 4326)
attr(null_sfc, "crs") <- NULL
na_sfc <- st_sfc(st_point(c(0, 0)))
bad_sf <- structure(list(a = 1), class = c("sf", "data.frame"), sf_column = "geom")
no_col <- structure(list(a = 1), class = c("sf", "data.frame"))
setClass("CRS", slots = c(projargs = "character"))
crs_plain <- new("CRS", projargs = "+proj=longlat")
crs_named <- new("CRS", projargs = "+proj=longlat")
comment(crs_named) <- crs4326$wkt
crs_unknown <- new("CRS", projargs = "+proj=merc")
comment(crs_unknown) <- merc$wkt

one <- function() {
  c(
    token("int", st_crs(4326L)),
    token("dbl", st_crs(4326)),
    token("half", st_crs(4326.5)),
    token("epsg", st_crs("EPSG:3857")),
    token("p4", st_crs("+proj=longlat +datum=WGS84")),
    token("ogc", st_crs("OGC:CRS84")),
    token("merc", st_crs("+proj=merc")),
    token("badproj", st_crs("+proj=ll")),
    token("big", st_crs(999999)),
    token("zero", st_crs(0)),
    token("nan", st_crs(NaN)),
    token("inf", st_crs(Inf)),
    token("ninf", st_crs(-Inf)),
    token("null", st_crs(NULL)),
    token("true", st_crs(TRUE)),
    token("false", st_crs(FALSE)),
    token("empty", st_crs("")),
    token("wgs", st_crs("WGS84")),
    token("len2", st_crs(c(4326, 3857))),
    token("num0", st_crs(numeric(0))),
    token("ch0", st_crs(character(0))),
    token("ch2", st_crs(c("EPSG:4326", "EPSG:3857"))),
    token("wktback", st_crs(crs4326$wkt)),
    token("mercback", st_crs(merc$wkt)),
    token("din", st_crs("EPSG:3857")$input),
    token("dp4", st_crs(3857)$proj4string),
    token("dname", st_crs(4326)$Name),
    token("depsg", st_crs(3857)$epsg),
    token("sfc", st_crs(sfc4326)),
    token("sf", st_crs(sf4326)),
    token("bbox", st_crs(bb)),
    token("bbox0", st_crs(bb0)),
    token("crsobj", st_crs(crs4326)),
    token("old", st_crs(old_sfc)),
    token("oldna", st_crs(old_na)),
    token("mat", st_crs(matrix(4326))),
    token("badsf", st_crs(bad_sf)),
    token("nocol", st_crs(no_col)),
    token("nullcrs", st_crs(null_sfc)),
    token("nullpar", st_crs(null_sfc, parameters = TRUE)),
    token("napar", st_crs(na_sfc, parameters = TRUE)),
    token("parign", st_crs(4326, parameters = TRUE)),
    token("p4326", st_crs(sfc4326, parameters = TRUE)),
    token("p3857", st_crs(st_sfc(st_point(c(0, 0)), crs = 3857), parameters = TRUE)),
    token("crs0", st_crs(crs_plain)),
    token("crs4326", st_crs(crs_named)),
    token("crsmerc", st_crs(crs_unknown)),
    token("lst", st_crs(list(1))),
    token("df", st_crs(data.frame(a = 1))),
    token("bigd", st_crs(1e20)),
    token("compound", st_crs("EPSG:4326+5703")),
    token("init", st_crs("+init=epsg:4326")),
    token("raster", st_crs(structure(list(), class = "Raster"))),
    token("spatial", st_crs(structure(list(), class = "Spatial"))),
    token("spat", st_crs(structure(list(), class = "SpatRaster"))),
    token("ob", st_crs("+proj=ob_tran +o_proj=longlat +o_lat_p=90 +o_lon_p=0"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE\n")
cat(value, sep = "\n")
cat("\nEND\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))

ex_in <- st_crs("EPSG:3857")$input
ex_p4 <- st_crs(3857)$proj4string
writeLines(
  c(
    paste0('st_crs("EPSG:3857")$input returns ', ex_in, "."),
    paste0("st_crs(3857)$proj4string returns ", ex_p4, ".")
  ),
  "/home/ahmed/killr_projects/killr/packages/sf/docs/output/st_crs-r.txt"
)
