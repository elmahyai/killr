# Proof: R interp::in.convex.hull on fixed triangulations and query points.
# Run from packages/interp: Rscript proof/in.convex.hull-r.R
source("proof/interp_proof_common.R")

cases <- point_cases()
cases <- Filter(function(cs) cs$id %in% c("rand60", "rand200", "grid5", "scaled40", "quad4", "dups-remove"), cases)

# Queries: the data points, a 12 x 12 lattice over the box grown by 0.5, and
# 40 Park-Miller points in the same box. grid5 has data points on hull edges,
# so the strict = FALSE path is exercised.
make_queries <- function(cs) {
  lo_x <- min(cs$x) - 0.5
  hi_x <- max(cs$x) + 0.5
  lo_y <- min(cs$y) - 0.5
  hi_y <- max(cs$y) + 0.5
  lat_x <- lo_x + (hi_x - lo_x) * (0:11) / 11
  lat_y <- lo_y + (hi_y - lo_y) * (0:11) / 11
  rnd <- lcg(80, 1234)
  list(
    x = c(cs$x, rep(lat_x, times = 12), lo_x + (hi_x - lo_x) * rnd[1:40]),
    y = c(cs$y, rep(lat_y, each = 12), lo_y + (hi_y - lo_y) * rnd[41:80])
  )
}

tris <- lapply(cases, function(cs) tri.mesh(cs$x, cs$y, duplicate = cs$dup))
qs <- lapply(cases, make_queries)

run_all <- function() {
  lapply(seq_along(tris), function(i) in.convex.hull(tris[[i]], qs[[i]]$x, qs[[i]]$y))
}
run_nonstrict <- function() {
  lapply(seq_along(tris), function(i) in.convex.hull(tris[[i]], qs[[i]]$x, qs[[i]]$y, strict = FALSE))
}
run_eps <- function() {
  lapply(seq_along(tris), function(i) in.convex.hull(tris[[i]], qs[[i]]$x, qs[[i]]$y, eps = 1e-3, strict = FALSE))
}

res <- run_all() # one untimed call, used for the records
res_ns <- run_nonstrict()
res_eps <- run_eps()

rec <- list()
for (i in seq_along(cases)) {
  id <- cases[[i]]$id
  rec[[paste0(id, "/query_x")]] <- qs[[i]]$x
  rec[[paste0(id, "/query_y")]] <- qs[[i]]$y
  rec[[paste0(id, "/strict")]] <- as.numeric(res[[i]])
  rec[[paste0(id, "/nonstrict")]] <- as.numeric(res_ns[[i]])
  rec[[paste0(id, "/nonstrict_eps1e-3")]] <- as.numeric(res_eps[[i]])
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/in.convex.hull-r.txt", rec, ms)
cat("R in.convex.hull cases:", length(cases), " inside:", sum(unlist(res)),
    " inside nonstrict:", sum(unlist(res_ns)), " median ms:", ms, "\n")
