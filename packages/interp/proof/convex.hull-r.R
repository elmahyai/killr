# Proof: R interp::convex.hull on fixed triangulations (plot.it = FALSE).
# Run from packages/interp: Rscript proof/convex.hull-r.R
source("proof/interp_proof_common.R")

cases <- point_cases()
cases <- Filter(function(cs) cs$id %in% c("rand60", "rand200", "grid5", "scaled40", "quad4", "dups-remove"), cases)

tris <- lapply(cases, function(cs) tri.mesh(cs$x, cs$y, duplicate = cs$dup))

run_all <- function() {
  lapply(tris, function(t) convex.hull(t))
}

res <- run_all() # one untimed call, used for the records

rec <- list()
for (i in seq_along(cases)) {
  id <- cases[[i]]$id
  rec[[paste0(id, "/x")]] <- res[[i]]$x
  rec[[paste0(id, "/y")]] <- res[[i]]$y
  rec[[paste0(id, "/i")]] <- as.numeric(res[[i]]$i)
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/convex.hull-r.txt", rec, ms)
cat("R convex.hull cases:", length(cases), " hull vertices:", sum(vapply(res, function(r) length(r$i), 1L)),
    " median ms:", ms, "\n")
