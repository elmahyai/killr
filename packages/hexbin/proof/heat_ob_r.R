# R reference for heat.ob(). Run from the repository root:
#   Rscript packages/hexbin/proof/heat_ob_r.R
source("packages/hexbin/proof/_proof_common.R")

put_str("case1", paste(heat.ob(10), collapse = " "))
put_str("case2", paste(heat.ob(7, beg = 20, end = 200), collapse = " "))
# A single row drops M to a vector, and M[, 1] then fails in R. Error, not a colour.
put_str("case3", tryCatch(paste(heat.ob(1), collapse = " "), error = function(e) "error"))
put_str("case4", paste(heat.ob(300, beg = 1, end = 256), collapse = " "))

record_timing(function() heat.ob(2000))
write_ref("heat_ob")
