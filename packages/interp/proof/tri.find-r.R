# Proof: R interp::tri.find on fixed triangulations and query points.
# Run from packages/interp: Rscript proof/tri.find-r.R
source("proof/interp_proof_common.R")

cases <- point_cases()
cases <- Filter(function(cs) cs$id %in% c("rand60", "rand200", "grid5", "scaled40", "dups-remove", "quad4"), cases)

# Queries: the data points, a 12 x 12 lattice over the box grown by 0.5, and
# 40 Park-Miller points in the same box. Many lattice and random points fall
# outside the hull, so the not-found path is covered.
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
  lapply(seq_along(tris), function(i) tri.find(tris[[i]], qs[[i]]$x, qs[[i]]$y))
}

res <- run_all() # one untimed call, used for the records

rec <- list()
for (i in seq_along(cases)) {
  id <- cases[[i]]$id
  r <- res[[i]]
  rec[[paste0(id, "/query_x")]] <- qs[[i]]$x
  rec[[paste0(id, "/query_y")]] <- qs[[i]]$y
  rec[[paste0(id, "/i1")]] <- as.numeric(r$i1)
  rec[[paste0(id, "/i2")]] <- as.numeric(r$i2)
  rec[[paste0(id, "/i3")]] <- as.numeric(r$i3)
  rec[[paste0(id, "/tr")]] <- as.numeric(r$tr)
  rec[[paste0(id, "/bc")]] <- rowmajor(r$bc)
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/tri.find-r.txt", rec, ms)
cat("R tri.find cases:", length(cases), " found:", sum(unlist(lapply(res, function(r) r$i1 != 0))),
    " not found:", sum(unlist(lapply(res, function(r) r$i1 == 0))), " median ms:", ms, "\n")
