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

bare <- function(n, directed, from, to) {
  e <- new.env(parent = emptyenv())
  structure(
    list(n, directed, from, to, NULL, NULL, NULL, NULL, NULL, e),
    class = "igraph"
  )
}

g_ring <- make_ring(10)
g_empty0 <- make_empty_graph(0)
g_empty1 <- make_empty_graph(1)
g_empty5 <- make_empty_graph(5)
g_dir <- make_ring(4, directed = TRUE)
g_named <- make_ring(7)
V(g_named)$name <- letters[1:7]
g_color <- set_vertex_attr(make_ring(10), "color", value = "red")
g_deleted <- delete_vertices(make_ring(10), 1:3)
g_added <- add_vertices(make_ring(3), 4)
g_full <- make_full_graph(6, directed = TRUE)
g_star <- make_star(8)
g_sub <- make_ring(4)
class(g_sub) <- c("foo", "igraph")
g_big <- make_empty_graph(100000)
g_slot <- make_ring(10)
g_slot[[1]] <- 99
clear_ptr <- function(g) {
  gx <- unclass(g)
  gx[[10]]$igraph <- NULL
  g
}
g_clear <- clear_ptr(make_ring(6))
g_len11 <- structure(replicate(11, NULL, simplify = FALSE), class = "igraph")
g_len0 <- structure(list(), class = "igraph")
g_len10 <- structure(replicate(10, NULL, simplify = FALSE), class = "igraph")
g_len12 <- structure(replicate(12, NULL, simplify = FALSE), class = "igraph")
g_env_list <- structure(
  list(1, FALSE, integer(0), integer(0), NULL, NULL, NULL, NULL, NULL, list()),
  class = "igraph"
)
g_atom10 <- structure(1:10, class = "igraph")
g_atom5 <- structure(1:5, class = "igraph")
g_atom11 <- structure(1:11, class = "igraph")
g_foo <- structure(list(), class = "foo")
g_r5 <- bare(5, FALSE, integer(0), integer(0))
g_r0 <- bare(0, FALSE, integer(0), integer(0))
g_frac <- bare(2.9, FALSE, integer(0), integer(0))
g_neg0 <- bare(-0, FALSE, integer(0), integer(0))
g_first <- bare(c(2, 9), FALSE, integer(0), integer(0))
g_neg <- bare(-1, FALSE, integer(0), integer(0))
g_na <- bare(NA_real_, FALSE, integer(0), integer(0))
g_nan <- bare(NaN, FALSE, integer(0), integer(0))
g_inf <- bare(Inf, FALSE, integer(0), integer(0))
g_ninf <- bare(-Inf, FALSE, integer(0), integer(0))
g_huge <- bare(1e20, FALSE, integer(0), integer(0))
g_intn <- bare(4L, FALSE, integer(0), integer(0))
g_nulln <- bare(NULL, FALSE, integer(0), integer(0))
g_dir_null <- bare(3, NULL, integer(0), integer(0))
g_dir_num <- bare(3, 1, integer(0), integer(0))
g_dir_int <- bare(3, 1L, integer(0), integer(0))
g_dir_two <- bare(4, c(TRUE, FALSE), integer(0), integer(0))
g_edges <- bare(3, FALSE, c(0L, 1L), c(1L, 2L))
g_edges_dbl <- bare(3, FALSE, c(0, 1), c(1, 2))
g_edges_frac <- bare(3, FALSE, c(0.5, 1), c(1, 2))
g_edges_tofrac <- bare(3, FALSE, c(0L, 1L), c(1, 0.5))
g_oor <- bare(2, FALSE, c(0L, 1L), c(1L, 2L))
g_neg_edge <- bare(3, FALSE, c(-1L, 0L), c(0L, 1L))
g_na_edge <- bare(3, FALSE, c(NA_integer_, 0L), c(1L, 2L))
g_self <- bare(1, FALSE, 0L, 0L)
g_tolong <- bare(3, FALSE, c(0L, 1L), c(1L, 2L, 0L))
g_r10000 <- bare(10000, FALSE, integer(0), integer(0))
g_r99999 <- bare(99999, FALSE, integer(0), integer(0))
g_r1e5 <- bare(1e5, FALSE, integer(0), integer(0))
g_r1e6 <- bare(1e6, FALSE, integer(0), integer(0))

one <- function() {
  parts <- c(
    paste0("ring10=", show(quote(gorder(g_ring)))),
    paste0("empty0=", show(quote(gorder(g_empty0)))),
    paste0("empty1=", show(quote(gorder(g_empty1)))),
    paste0("empty5=", show(quote(gorder(g_empty5)))),
    paste0("directed=", show(quote(gorder(g_dir)))),
    paste0("named=", show(quote(gorder(g_named)))),
    paste0("color=", show(quote(gorder(g_color)))),
    paste0("deleted=", show(quote(gorder(g_deleted)))),
    paste0("added=", show(quote(gorder(g_added)))),
    paste0("full=", show(quote(gorder(g_full)))),
    paste0("star=", show(quote(gorder(g_star)))),
    paste0("subclass=", show(quote(gorder(g_sub)))),
    paste0("big=", show(quote(gorder(g_big)))),
    paste0("slot99=", show(quote(gorder(g_slot)))),
    paste0("named_arg=", show(quote(gorder(graph = g_ring)))),
    paste0("cleared=", show(quote(gorder(g_clear)))),
    paste0("restore5=", show(quote(gorder(g_r5)))),
    paste0("restore0=", show(quote(gorder(g_r0)))),
    paste0("frac=", show(quote(gorder(g_frac)))),
    paste0("neg0=", show(quote(gorder(g_neg0)))),
    paste0("first=", show(quote(gorder(g_first)))),
    paste0("neg=", show(quote(gorder(g_neg)))),
    paste0("na_n=", show(quote(gorder(g_na)))),
    paste0("nan_n=", show(quote(gorder(g_nan)))),
    paste0("inf_n=", show(quote(gorder(g_inf)))),
    paste0("ninf_n=", show(quote(gorder(g_ninf)))),
    paste0("huge=", show(quote(gorder(g_huge)))),
    paste0("int_n=", show(quote(gorder(g_intn)))),
    paste0("null_n=", show(quote(gorder(g_nulln)))),
    paste0("dir_null=", show(quote(gorder(g_dir_null)))),
    paste0("dir_num=", show(quote(gorder(g_dir_num)))),
    paste0("dir_int=", show(quote(gorder(g_dir_int)))),
    paste0("dir_two=", show(quote(gorder(g_dir_two)))),
    paste0("edges=", show(quote(gorder(g_edges)))),
    paste0("edges_dbl=", show(quote(gorder(g_edges_dbl)))),
    paste0("oor=", show(quote(gorder(g_oor)))),
    paste0("neg_edge=", show(quote(gorder(g_neg_edge)))),
    paste0("na_edge=", show(quote(gorder(g_na_edge)))),
    paste0("self=", show(quote(gorder(g_self)))),
    paste0("tolong=", show(quote(gorder(g_tolong)))),
    paste0("n10000=", show(quote(gorder(g_r10000)))),
    paste0("n99999=", show(quote(gorder(g_r99999)))),
    paste0("n1e5=", show(quote(gorder(g_r1e5)))),
    paste0("n1e6=", show(quote(gorder(g_r1e6)))),
    paste0("len11=", show(quote(gorder(g_len11)))),
    paste0("len0=", show(quote(gorder(g_len0)))),
    paste0("len10=", show(quote(gorder(g_len10)))),
    paste0("len12=", show(quote(gorder(g_len12)))),
    paste0("env_list=", show(quote(gorder(g_env_list)))),
    paste0("atom10=", show(quote(gorder(g_atom10)))),
    paste0("atom5=", show(quote(gorder(g_atom5)))),
    paste0("atom11=", show(quote(gorder(g_atom11)))),
    paste0("foo=", show(quote(gorder(g_foo)))),
    paste0("null=", show(quote(gorder(NULL)))),
    paste0("missing=", show(quote(gorder()))),
    paste0("missing_arg=", show(quote(gorder(rlang::missing_arg())))),
    paste0("numeric=", show(quote(gorder(numeric(10))))),
    paste0("number=", show(quote(gorder(1)))),
    paste0("list=", show(quote(gorder(list())))),
    paste0("data_frame=", show(quote(gorder(data.frame(a = 1))))),
    paste0("na=", show(quote(gorder(NA)))),
    paste0("character=", show(quote(gorder("igraph")))),
    paste0("edges_frac=", show(quote(gorder(g_edges_frac)))),
    paste0("edges_tofrac=", show(quote(gorder(g_edges_tofrac))))
  )
  paste(parts, collapse = "|")
}

example <- capture.output({
  g <- make_ring(10)
  print(gorder(g))
  print(vcount(g))
})
writeLines(
  example,
  "/home/ahmed/killr_projects/killr/packages/igraph/docs/output/gorder-r.txt"
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
