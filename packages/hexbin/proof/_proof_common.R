# Shared helpers for the hexbin R-side proofs. Run from the repository root.
# Each proof writes packages/hexbin/docs/output/<name>-r.txt, one line per value:
#   <key> num <values...>   numbers, NA written as NA, %.17g precision
#   <key> str <text>        strings
# and a timing line: timing_r_median_s num <seconds>.

suppressPackageStartupMessages(library(hexbin))

OUT_DIR <- "packages/hexbin/docs/output"
.ref <- new.env()
.ref$lines <- character(0)

# Fixed points, identical to the Python side. Integer products are exact in double.
points_fixed <- function(n) {
  k <- as.numeric(1:n)
  x <- ((k * 7919) %% 10007) / 10007 * 10 - 5
  y <- ((k * 104729) %% 10009) / 10009 * 6 - 3
  list(x = x, y = y)
}

put_num <- function(key, v) {
  v <- as.numeric(v)
  tok <- ifelse(is.na(v), "NA", sprintf("%.17g", v))
  .ref$lines <- c(.ref$lines, paste(key, "num", paste(tok, collapse = " ")))
  invisible(NULL)
}

put_str <- function(key, s) {
  .ref$lines <- c(.ref$lines, paste(key, "str", s))
  invisible(NULL)
}

# A hexbin S4 object, slot by slot. Prefix names the case.
record_hexbin <- function(prefix, h) {
  put_num(paste0(prefix, ".cell"), h@cell)
  put_num(paste0(prefix, ".count"), h@count)
  put_num(paste0(prefix, ".xcm"), h@xcm)
  put_num(paste0(prefix, ".ycm"), h@ycm)
  put_num(paste0(prefix, ".xbins"), h@xbins)
  put_num(paste0(prefix, ".shape"), h@shape)
  put_num(paste0(prefix, ".xbnds"), h@xbnds)
  put_num(paste0(prefix, ".ybnds"), h@ybnds)
  put_num(paste0(prefix, ".dimen"), h@dimen)
  put_num(paste0(prefix, ".n"), h@n)
  put_num(paste0(prefix, ".ncells"), h@ncells)
  if (!is.null(h@cID)) put_num(paste0(prefix, ".cID"), h@cID)
  invisible(NULL)
}

# The numeric slots of a hexVP, as the Python side reads them. mar is in lines and plt is in npc,
# the units hexViewport() stores. Grid unit conversion is not translated, so these are the inputs.
record_hexvp <- function(prefix, hv) {
  put_num(paste0(prefix, ".mar"), as.numeric(hv@mar))
  put_num(paste0(prefix, ".plt"), as.numeric(hv@plt))
  put_num(paste0(prefix, ".xscale"), hv@xscale)
  put_num(paste0(prefix, ".yscale"), hv@yscale)
  put_num(paste0(prefix, ".shape"), hv@shape)
  invisible(NULL)
}

# Median of 20 timed calls after one untimed call. Sys.time() is the clock.
time_median <- function(f, reps = 20) {
  f()
  t <- numeric(reps)
  for (i in seq_len(reps)) {
    t0 <- Sys.time()
    f()
    t[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  }
  median(t)
}

record_timing <- function(f) {
  m <- time_median(f)
  put_num("timing_r_median_s", m)
  cat(sprintf("R median seconds (20 timed calls, Sys.time): %.9f\n", m))
  invisible(m)
}

write_ref <- function(name) {
  path <- file.path(OUT_DIR, paste0(name, "-r.txt"))
  writeLines(c(paste0("# R hexbin ", as.character(packageVersion("hexbin")), " reference: ", name),
               .ref$lines), path)
  cat("wrote", path, "\n")
}
