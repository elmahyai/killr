# R reference for LinGray(). Run from the repository root:
#   Rscript packages/hexbin/proof/LinGray_r.R
source("packages/hexbin/proof/_proof_common.R")

put_str("case1", paste(LinGray(20), collapse = " "))
put_str("case2", paste(LinGray(7, beg = 90, end = 15), collapse = " "))
# A single row drops M to a vector, and M[, 1] then fails in R. Error, not a colour.
put_str("case3", tryCatch(paste(LinGray(1), collapse = " "), error = function(e) "error"))
put_str("case4", paste(LinGray(300, beg = 1, end = 92), collapse = " "))
# The table has 101 rows; reading past it is an error in R (rgb() gets NA).
put_str("case5", tryCatch(paste(LinGray(5, beg = 1, end = 256), collapse = " "),
                          error = function(e) "error"))

record_timing(function() LinGray(2000))
write_ref("LinGray")
