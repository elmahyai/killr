# Used only by check_tnf.py: R parse and Rd example extraction match tools 4.5.0.
suppressPackageStartupMessages(library(tools))

args <- commandArgs(trailingOnly = TRUE)
cmd <- args[[1L]]

find_TnF_in_code <- function(file, txt) {
    matches <- list()
    TnF <- c("T", "F")
    find_bad_exprs <- function(e, p) {
        if (is.name(e) && (as.character(e) %in% TnF) && !is.null(p)) {
            matches <<- c(matches, list(p))
        } else if (is.recursive(e)) {
            for (i in seq_along(e)) Recall(e[[i]], e)
        }
    }
    exprs <- if (missing(txt)) {
        tryCatch(
            parse(file = file, n = -1L),
            error = function(e) stop(
                gettextf(
                    "parse error in file '%s':\n%s",
                    file,
                    tools:::.massage_file_parse_error_message(conditionMessage(e))
                ),
                domain = NA,
                call. = FALSE
            )
        )
    } else {
        tryCatch(
            str2expression(txt),
            error = function(e) stop(
                gettextf(
                    "parse error in examples from file '%s':\n%s",
                    file,
                    conditionMessage(e)
                ),
                domain = NA,
                call. = FALSE
            )
        )
    }
    for (i in seq_along(exprs)) find_bad_exprs(exprs[[i]], NULL)
    matches
}

deparsed <- function(matches) {
    if (!length(matches)) {
        return(character())
    }
    vapply(
        matches,
        function(e) paste(deparse(e, width.cutoff = 500L), collapse = ""),
        character(1L)
    )
}

if (cmd == "find") {
    file <- args[[2L]]
    text <- args[[3L]]
    if (identical(text, "")) {
        matches <- find_TnF_in_code(file)
    } else {
        matches <- find_TnF_in_code(file, text)
    }
    writeLines(deparsed(matches))
    quit(save = "no", status = 0L)
}

if (cmd == "examples") {
    path <- args[[2L]]
    Rd <- tools:::prepare_Rd(path, defines = .Platform$OS.type)
    txt <- tools:::.Rd_get_example_code(Rd)
    cat(txt)
    quit(save = "no", status = 0L)
}

stop("unknown command")
