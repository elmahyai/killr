pkg <- tempfile(); untar("../../../rcran/contrib/htmlTable_2.5.0.tar.gz", exdir=pkg)
source(file.path(pkg, "htmlTable/R/txtFrmt.R"))
one <- as.character(txtMergeLines("hello","world"))
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); txtMergeLines("hello","world"); times[i] <- as.numeric(Sys.time()-t)*1000 }
cat(jsonlite::toJSON(list(value=one, r_ms=median(times)), auto_unbox=TRUE), "\n")
