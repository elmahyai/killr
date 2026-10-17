# R reference for hexpolygon(). Run from the repository root:
#   Rscript packages/hexbin/proof/hexpolygon_r.R
# hexpolygon() is run unchanged. Only the names it calls for drawing (grid.polygon and polygon)
# are resolved to recorders, so the vertices R would draw are written instead of drawn.
source("packages/hexbin/proof/_proof_common.R")

capture_into <- function(prefix) {
  e <- new.env(parent = asNamespace("hexbin"))
  e$grid.polygon <- function(x, y, id.lengths = NULL, ...) {
    put_num(paste0(prefix, ".x"), as.numeric(x))
    put_num(paste0(prefix, ".y"), as.numeric(y))
    if (!is.null(id.lengths)) put_num(paste0(prefix, ".id"), id.lengths)
    invisible(NULL)
  }
  e$polygon <- function(x, y, ...) {
    put_num(paste0(prefix, ".x"), as.numeric(x))
    put_num(paste0(prefix, ".y"), as.numeric(y))
    invisible(NULL)
  }
  e
}

# Draws nothing, but forces the coordinates, so the timing includes building them as R does.
drop_into <- function() {
  e <- new.env(parent = asNamespace("hexbin"))
  e$grid.polygon <- function(x, y, id.lengths = NULL, ...) {
    force(x); force(y); force(id.lengths)
    invisible(NULL)
  }
  e$polygon <- function(x, y, ...) {
    force(x); force(y)
    invisible(NULL)
  }
  e
}

x3 <- c(0, 1, 2.5)
y3 <- c(0, 0.5, -1)

hp1 <- hexpolygon; environment(hp1) <- capture_into("case1")
hp1(x3, y3, hexC = hexcoords(0.3, n = 1))            # grid path, hUnit = "native"

hp2 <- hexpolygon; environment(hp2) <- capture_into("case2")
hp2(x3, y3, hexC = hexcoords(0.3, 0.2, n = 1), hUnit = NULL)   # grid path, plain numbers

hp3 <- hexpolygon; environment(hp3) <- capture_into("case3")
hp3(x3, y3, hexC = hexcoords(dx = 0.2, dy = 0.15, n = 1, sep = NA))  # traditional path, NA separator

hp4 <- hexpolygon; environment(hp4) <- capture_into("case4")
hp4(x3, y3, dx = 0.25)                               # default hexC, dy = dx / sqrt(3)

p <- points_fixed(2000)
hpt <- hexpolygon; environment(hpt) <- drop_into()
record_timing(function() hpt(p$x, p$y, dx = 0.1))
write_ref("hexpolygon")
