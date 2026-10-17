# Proof: R interp::triSht2tri on the triangulations of the fixed point sets.
# Run from packages/interp.
source("proof/interp_proof_common.R")

cases <- point_cases()
cases <- Filter(function(cs) cs$id != "dups-strip", cases)

# Triangulations are built untimed; only triSht2tri is timed.
tris <- lapply(cases, function(cs) tri.mesh(cs$x, cs$y, duplicate = cs$dup))

run_all <- function() lapply(tris, function(t) triSht2tri(t))

res <- run_all() # one untimed call, used for the records

rec <- list()
for (i in seq_along(cases)) {
  id <- cases[[i]]$id
  o <- res[[i]]
  rec[[paste0(id, "/n")]] <- o$n
  rec[[paste0(id, "/x")]] <- o$x
  rec[[paste0(id, "/y")]] <- o$y
  rec[[paste0(id, "/tlist")]] <- o$tlist
  rec[[paste0(id, "/tlptr")]] <- o$tlptr
  rec[[paste0(id, "/tlend")]] <- o$tlend
  rec[[paste0(id, "/tlnew")]] <- o$tlnew
  rec[[paste0(id, "/adjlen")]] <- vapply(o$adjlist, length, integer(1))
  rec[[paste0(id, "/adj")]] <- unlist(o$adjlist)
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/triSht2tri-r.txt", rec, ms)
cat("R triSht2tri cases:", length(cases), " median ms:", ms, "\n")
