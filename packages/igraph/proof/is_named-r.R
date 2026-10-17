.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(igraph))
if (as.character(packageVersion("igraph")) != "2.3.4") {
  stop("expected igraph 2.3.4")
}

show <- function(expr) {
  tryCatch(
    {
      val <- eval(expr, envir = parent.frame())
      if (isTRUE(val)) {
        "TRUE"
      } else if (identical(val, FALSE)) {
        "FALSE"
      } else {
        paste0("VAL ", paste(deparse(val), collapse = " "))
      }
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

g_ring <- make_ring(10)
g_named <- make_ring(10)
V(g_named)$name <- letters[1:10]
g_color <- set_vertex_attr(make_ring(10), "color", value = "red")
g_edge <- set_edge_attr(make_ring(10), "name", value = letters[1:10])
g_Name <- set_vertex_attr(make_ring(10), "Name", value = "X")
g_names <- set_vertex_attr(make_ring(10), "names", value = "X")
g_na <- set_vertex_attr(make_ring(10), "name", value = rep(NA_character_, 10))
g_num <- set_vertex_attr(make_ring(10), "name", value = seq_len(10))
g_deleted <- delete_vertex_attr(g_named, "name")
g_empty <- make_empty_graph(0)
g_empty_named <- set_vertex_attr(make_empty_graph(0), "name", value = character(0))
g_color_name <- set_vertex_attr(
  set_vertex_attr(make_ring(10), "color", value = "red"),
  "name",
  value = letters[1:10]
)
g_name_color <- set_vertex_attr(
  set_vertex_attr(make_ring(10), "name", value = letters[1:10]),
  "color",
  value = "red"
)
g_space <- set_vertex_attr(make_ring(3), "name ", value = "a")
g_lead <- set_vertex_attr(make_ring(3), " name", value = "a")
g_blank <- set_vertex_attr(make_ring(3), "", value = "a")
g_dir <- make_ring(4, directed = TRUE)
g_dir_named <- make_ring(4, directed = TRUE)
V(g_dir_named)$name <- letters[1:4]
g_sub <- make_ring(4)
class(g_sub) <- c("foo", "igraph")
g_sub_named <- make_ring(4)
class(g_sub_named) <- c("foo", "igraph")
V(g_sub_named)$name <- letters[1:4]
g_len11 <- structure(replicate(11, NULL, simplify = FALSE), class = "igraph")
g_len0 <- structure(list(), class = "igraph")
g_len10 <- structure(replicate(10, NULL, simplify = FALSE), class = "igraph")

one <- function() {
  parts <- c(
    paste0("ring=", show(quote(is_named(g_ring)))),
    paste0("named=", show(quote(is_named(g_named)))),
    paste0("color=", show(quote(is_named(g_color)))),
    paste0("edge_name=", show(quote(is_named(g_edge)))),
    paste0("Name=", show(quote(is_named(g_Name)))),
    paste0("names=", show(quote(is_named(g_names)))),
    paste0("na_name=", show(quote(is_named(g_na)))),
    paste0("num_name=", show(quote(is_named(g_num)))),
    paste0("deleted=", show(quote(is_named(g_deleted)))),
    paste0("empty=", show(quote(is_named(g_empty)))),
    paste0("empty_named=", show(quote(is_named(g_empty_named)))),
    paste0("color_name=", show(quote(is_named(g_color_name)))),
    paste0("name_color=", show(quote(is_named(g_name_color)))),
    paste0("space=", show(quote(is_named(g_space)))),
    paste0("lead_space=", show(quote(is_named(g_lead)))),
    paste0("blank=", show(quote(is_named(g_blank)))),
    paste0("directed=", show(quote(is_named(g_dir)))),
    paste0("directed_named=", show(quote(is_named(g_dir_named)))),
    paste0("subclass=", show(quote(is_named(g_sub)))),
    paste0("subclass_named=", show(quote(is_named(g_sub_named)))),
    paste0("len11=", show(quote(is_named(g_len11)))),
    paste0("len0=", show(quote(is_named(g_len0)))),
    paste0("len10=", show(quote(is_named(g_len10)))),
    paste0("null=", show(quote(is_named(NULL)))),
    paste0("missing=", show(quote(is_named()))),
    paste0("numeric=", show(quote(is_named(numeric(10))))),
    paste0("list=", show(quote(is_named(list())))),
    paste0("data_frame=", show(quote(is_named(data.frame(a = 1))))),
    paste0("na=", show(quote(is_named(NA)))),
    paste0("character=", show(quote(is_named("igraph"))))
  )
  paste(parts, collapse = "|")
}

example <- capture.output({
  g <- make_ring(10)
  print(is_named(g))
  V(g)$name <- letters[1:10]
  print(is_named(g))
  print(neighbors(g, "a"))
})
writeLines(
  example,
  "/home/ahmed/killr_projects/killr/packages/igraph/docs/output/is_named-r.txt"
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
