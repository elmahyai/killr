# Shared R side of the shuffle proofs. Each case sets R's seed, calls the
# function once, then draws one runif(1) so the RNG position is compared too.
# Values are written row-major, one case per line: name<TAB>v1,v2,...

run_proof <- function(fn_name, cases, out_dir) {
    values_path <- file.path(out_dir, paste0(fn_name, "-r-values.txt"))
    timing_path <- file.path(out_dir, paste0(fn_name, "-r-timing.tsv"))

    run_one <- function(cs) {
        set.seed(cs$seed)
        res <- suppressMessages(cs$f())
        c(as.vector(t(as.matrix(res))), runif(1))
    }

    lines <- vapply(cases, function(cs) {
        paste(cs$name, paste(sprintf("%.17g", run_one(cs)), collapse = ","), sep = "\t")
    }, "")
    writeLines(lines, values_path)

    # one pass runs every case once; set.seed is outside the timed region
    pass <- function() {
        total <- 0
        for (cs in cases) {
            set.seed(cs$seed)
            t0 <- Sys.time()
            suppressMessages(cs$f())
            t1 <- Sys.time()
            total <- total + as.numeric(difftime(t1, t0, units = "secs")) * 1000
        }
        total
    }
    pass()  # untimed
    ms <- vapply(seq_len(20), function(i) pass(), 0)
    r_ms <- median(ms)
    writeLines(c("function\tr_ms", sprintf("%s\t%.9f", fn_name, r_ms)), timing_path)
    invisible(r_ms)
}
