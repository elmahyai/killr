.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(igraph))
if (as.character(packageVersion("igraph")) != "2.3.4") {
  stop("expected igraph 2.3.4")
}

show <- function(expr) {
  tryCatch(
    {
      val <- eval(expr, envir = parent.frame())
      paste0(
        "VAL ", paste(deparse(val), collapse = " "),
        " TYPE ", typeof(val),
        " LEN ", length(val),
        " NAMES ", if (is.null(names(val))) "NULL" else paste(names(val), collapse = ","),
        " MODE ", storage.mode(val)
      )
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

bare <- function(n, directed, from = integer(0), to = integer(0)) {
  e <- new.env(parent = emptyenv())
  structure(
    list(n, directed, from, to, NULL, NULL, NULL, NULL, NULL, e),
    class = "igraph"
  )
}

clear_ptr <- function(g) {
  gx <- unclass(g)
  gx[[10]]$igraph <- NULL
  g
}

g_ring <- make_ring(10)
g_dir <- make_ring(10, directed = TRUE)
g_empty <- make_empty_graph(0)
g_empty_f <- make_empty_graph(0, directed = FALSE)
g_full <- make_full_graph(4, directed = TRUE)
g_star <- make_star(5, mode = "out")
g_star_u <- make_star(5, mode = "undirected")
g_named <- make_ring(4, directed = TRUE)
V(g_named)$name <- letters[1:4]
g_sub <- make_ring(3, directed = TRUE)
class(g_sub) <- c("foo", "igraph")
g_slot_u <- make_ring(6)
g_slot_u[[2]] <- TRUE
g_slot_d <- make_ring(6, directed = TRUE)
g_slot_d[[2]] <- FALSE
g_clear_u <- clear_ptr(make_ring(4))
g_clear_d <- clear_ptr(make_ring(4, directed = TRUE))
g_clear_flip <- clear_ptr(make_ring(4))
g_clear_flip[[2]] <- TRUE
g_len11 <- structure(replicate(11, NULL, simplify = FALSE), class = "igraph")
g_len0 <- structure(list(), class = "igraph")
g_len10 <- structure(replicate(10, NULL, simplify = FALSE), class = "igraph")
g_len12 <- structure(replicate(12, NULL, simplify = FALSE), class = "igraph")
g_env_list <- structure(
  list(1, TRUE, integer(0), integer(0), NULL, NULL, NULL, NULL, NULL, list()),
  class = "igraph"
)
g_atom10 <- structure(1:10, class = "igraph")
g_atom11 <- structure(1:11, class = "igraph")
g_atom5 <- structure(1:5, class = "igraph")
g_foo <- structure(list(), class = "foo")
g_bare_f <- bare(3, FALSE)
g_bare_t <- bare(3, TRUE)
g_bare_na <- bare(3, NA)
g_bare_two <- bare(4, c(TRUE, FALSE))
g_bare_twof <- bare(4, c(FALSE, TRUE))
g_bare_natrue <- bare(2, c(NA, TRUE))
g_na_edges <- bare(3, NA, c(0L, 1L), c(1L, 0L))
g_n_first <- bare(c(5, 1), c(FALSE, TRUE))
g_neg0 <- bare(-0, TRUE)
g_frac <- bare(2.9, FALSE)
g_edges <- bare(3, TRUE, c(0L, 1L), c(1L, 2L))
g_edges_u <- bare(3, FALSE, c(0L, 1L), c(1L, 2L))
g_dbl <- bare(3, TRUE, c(0, 1), c(1, 2))
g_self <- bare(1, TRUE, 0L, 0L)
g_tolong <- bare(3, TRUE, c(0L, 1L), c(1L, 2L, 0L))
g_dir_null <- bare(3, NULL)
g_dir_num <- bare(3, 1)
g_dir_int <- bare(3, 1L)
g_dir_char <- bare(2, "TRUE")
g_dir_list <- bare(2, list(TRUE))
g_dir_cplx <- bare(2, 1 + 0i)
g_int_n <- bare(4L, "x")
g_null_n <- bare(NULL, TRUE)
g_char_n <- bare("3", TRUE)
g_log_n <- bare(TRUE, TRUE)
g_na_char <- bare(NA_real_, "x")
g_neg_null <- bare(-1, NULL)
g_neg <- bare(-1, TRUE)
g_na_n <- bare(NA_real_, TRUE)
g_nan_n <- bare(NaN, FALSE)
g_inf_n <- bare(Inf, TRUE)
g_ninf <- bare(-Inf, TRUE)
g_huge <- bare(1e20, FALSE)
g_oor <- bare(2, TRUE, c(0L, 1L), c(1L, 2L))
g_neg_edge <- bare(3, TRUE, c(-1L, 0L), c(0L, 1L))
g_na_edge <- bare(3, FALSE, c(NA_integer_, 0L), c(1L, 2L))
g_frac_e <- bare(3, TRUE, c(0.5, 1), c(1, 2))
g_tofrac <- bare(3, FALSE, c(0L, 1L), c(1, 0.5))

cache_bit <- function() {
  g <- bare(4, TRUE, integer(0), integer(0))
  first <- is_directed(g)
  g[[2]] <- FALSE
  second <- is_directed(g)
  slot <- unclass(g)[[2]]
  paste0(
    "first=", paste(deparse(first), collapse = " "),
    ",second=", paste(deparse(second), collapse = " "),
    ",slot=", paste(deparse(slot), collapse = " ")
  )
}

one <- function() {
  parts <- c(
    paste0("ring=", show(quote(is_directed(g_ring)))),
    paste0("directed=", show(quote(is_directed(g_dir)))),
    paste0("empty=", show(quote(is_directed(g_empty)))),
    paste0("empty_f=", show(quote(is_directed(g_empty_f)))),
    paste0("full=", show(quote(is_directed(g_full)))),
    paste0("star_out=", show(quote(is_directed(g_star)))),
    paste0("star_u=", show(quote(is_directed(g_star_u)))),
    paste0("named=", show(quote(is_directed(g_named)))),
    paste0("subclass=", show(quote(is_directed(g_sub)))),
    paste0("slot_u=", show(quote(is_directed(g_slot_u)))),
    paste0("slot_d=", show(quote(is_directed(g_slot_d)))),
    paste0("named_arg=", show(quote(is_directed(graph = g_dir)))),
    paste0("clear_u=", show(quote(is_directed(g_clear_u)))),
    paste0("clear_d=", show(quote(is_directed(g_clear_d)))),
    paste0("clear_flip=", show(quote(is_directed(g_clear_flip)))),
    paste0("cache=", cache_bit()),
    paste0("bare_f=", show(quote(is_directed(g_bare_f)))),
    paste0("bare_t=", show(quote(is_directed(g_bare_t)))),
    paste0("bare_na=", show(quote(is_directed(g_bare_na)))),
    paste0("bare_two=", show(quote(is_directed(g_bare_two)))),
    paste0("bare_twof=", show(quote(is_directed(g_bare_twof)))),
    paste0("bare_natrue=", show(quote(is_directed(g_bare_natrue)))),
    paste0("na_edges=", show(quote(is_directed(g_na_edges)))),
    paste0("n_first=", show(quote(is_directed(g_n_first)))),
    paste0("neg0=", show(quote(is_directed(g_neg0)))),
    paste0("frac=", show(quote(is_directed(g_frac)))),
    paste0("edges=", show(quote(is_directed(g_edges)))),
    paste0("edges_u=", show(quote(is_directed(g_edges_u)))),
    paste0("dbl_edges=", show(quote(is_directed(g_dbl)))),
    paste0("self=", show(quote(is_directed(g_self)))),
    paste0("tolong=", show(quote(is_directed(g_tolong)))),
    paste0("len11=", show(quote(is_directed(g_len11)))),
    paste0("len0=", show(quote(is_directed(g_len0)))),
    paste0("len10=", show(quote(is_directed(g_len10)))),
    paste0("len12=", show(quote(is_directed(g_len12)))),
    paste0("env_list=", show(quote(is_directed(g_env_list)))),
    paste0("atom10=", show(quote(is_directed(g_atom10)))),
    paste0("atom11=", show(quote(is_directed(g_atom11)))),
    paste0("atom5=", show(quote(is_directed(g_atom5)))),
    paste0("foo=", show(quote(is_directed(g_foo)))),
    paste0("null=", show(quote(is_directed(NULL)))),
    paste0("missing=", show(quote(is_directed()))),
    paste0("missarg=", show(quote(is_directed(rlang::missing_arg())))),
    paste0("numeric=", show(quote(is_directed(numeric(10))))),
    paste0("number=", show(quote(is_directed(1)))),
    paste0("list=", show(quote(is_directed(list())))),
    paste0("data_frame=", show(quote(is_directed(data.frame(a = 1))))),
    paste0("na=", show(quote(is_directed(NA)))),
    paste0("character=", show(quote(is_directed("igraph")))),
    paste0("dir_null=", show(quote(is_directed(g_dir_null)))),
    paste0("dir_num=", show(quote(is_directed(g_dir_num)))),
    paste0("dir_int=", show(quote(is_directed(g_dir_int)))),
    paste0("dir_char=", show(quote(is_directed(g_dir_char)))),
    paste0("dir_list=", show(quote(is_directed(g_dir_list)))),
    paste0("dir_cplx=", show(quote(is_directed(g_dir_cplx)))),
    paste0("int_n=", show(quote(is_directed(g_int_n)))),
    paste0("null_n=", show(quote(is_directed(g_null_n)))),
    paste0("char_n=", show(quote(is_directed(g_char_n)))),
    paste0("log_n=", show(quote(is_directed(g_log_n)))),
    paste0("na_char=", show(quote(is_directed(g_na_char)))),
    paste0("neg_null=", show(quote(is_directed(g_neg_null)))),
    paste0("neg=", show(quote(is_directed(g_neg)))),
    paste0("na_n=", show(quote(is_directed(g_na_n)))),
    paste0("nan_n=", show(quote(is_directed(g_nan_n)))),
    paste0("inf_n=", show(quote(is_directed(g_inf_n)))),
    paste0("ninf=", show(quote(is_directed(g_ninf)))),
    paste0("huge=", show(quote(is_directed(g_huge)))),
    paste0("oor=", show(quote(is_directed(g_oor)))),
    paste0("neg_edge=", show(quote(is_directed(g_neg_edge)))),
    paste0("na_edge=", show(quote(is_directed(g_na_edge)))),
    paste0("edges_frac=", show(quote(is_directed(g_frac_e)))),
    paste0("tofrac=", show(quote(is_directed(g_tofrac))))
  )
  paste(parts, collapse = "|")
}

example <- capture.output({
  g <- make_ring(10)
  print(is_directed(g))
  g2 <- make_ring(10, directed = TRUE)
  print(is_directed(g2))
})
writeLines(
  example,
  "/home/ahmed/killr_projects/killr/packages/igraph/docs/output/is_directed-r.txt"
)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- gsub("\n", "\\n", value, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
