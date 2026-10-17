suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_str <- function(s) {
  if (length(s) != 1L) stop("json_str expects length 1")
  if (is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
json_num <- function(x) sprintf("%.17g", x)
json_mat <- function(m) {
  m <- as.matrix(m)
  if (nrow(m) == 0L) {
    return("[]")
  }
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

demo_summary <- function(x, type) {
  n <- length(x)
  ns <- asNamespace("colorspace")
  if (type == "map") {
    z <- stats::na.omit(colorspace::USSouthPolygon$z)
    list(type = type, colors = as.character(x[cut(z, breaks = 0:n/n)]))
  } else if (type == "heatmap") {
    list(type = type, colors = as.character(rev(x)))
  } else if (type == "scatter") {
    get("plot_scatter", envir = ns)(x)
    dat <- get(".example_env", envir = ns)$xyhclust
    cl <- cutree(attr(dat, "hclust"), n)
    list(type = type, colors = as.character(x[cl]))
  } else if (type == "spine") {
    list(type = type, colors = as.character(rep(x, 9)), border_black = n < 10)
  } else if (type == "bar") {
    m <- demoplot(x, type = "bar")
    list(type = type, colors = as.character(x), matrix = as.matrix(m))
  } else if (type == "pie") {
    list(type = type, colors = as.character(x))
  } else if (type == "perspective") {
    grid_n <- 31
    x1 <- x2 <- seq(-3, 3, length.out = grid_n)
    y <- outer(x1, x2, function(x, y) {
      0.5 * stats::dnorm(x, -1, 0.8) * stats::dnorm(y, -1, 0.8) +
        0.5 * stats::dnorm(x, 1, 0.72) * stats::dnorm(y, 1, 0.72)
    })
    if (n > 1) {
      facet <- cut(
        y[-1, -1] + y[-1, -grid_n] + y[-grid_n, -1] + y[-grid_n, -grid_n],
        n
      )
      list(type = type, colors = as.character(rev(x)[facet]))
    } else {
      list(type = type, colors = as.character(x))
    }
  } else if (type == "mosaic") {
    get("plot_mosaic", envir = ns)(x)
    mat <- get(".example_env", envir = ns)$msc.matrix[[n]]
    list(
      type = type,
      colors = as.character(x),
      matrix_shape = as.integer(dim(mat))
    )
  } else if (type == "lines") {
    list(type = type, colors = as.character(c(x, rev(x), rev(x))))
  } else {
    stop("unknown type")
  }
}

one <- function() {
  x7 <- diverging_hcl(7)
  x1 <- diverging_hcl(1)
  list(
    map = demo_summary(x7, "map"),
    heatmap = demo_summary(x7, "heatmap"),
    scatter = demo_summary(x7, "scatter"),
    spine = demo_summary(x7, "spine"),
    bar = demo_summary(x7, "bar"),
    pie = demo_summary(x7, "pie"),
    perspective = demo_summary(x7, "perspective"),
    mosaic = demo_summary(x7, "mosaic"),
    lines = demo_summary(x7, "lines"),
    perspective_single = demo_summary(x1, "perspective")
  )
}

block_json <- function(block) {
  parts <- c(
    paste0('"type":', json_str(block$type)),
    paste0('"colors":', json_vec(block$colors))
  )
  if (!is.null(block[["matrix"]]) && length(block[["matrix"]])) {
    parts <- c(parts, paste0('"matrix":', json_mat(block[["matrix"]])))
  }
  if (!is.null(block[["matrix_shape"]])) {
    parts <- c(
      parts,
      paste0(
        '"matrix_shape":[',
        paste(vapply(block[["matrix_shape"]], json_num, ""), collapse = ","),
        "]"
      )
    )
  }
  if (!is.null(block[["border_black"]])) {
    parts <- c(
      parts,
      paste0('"border_black":', tolower(as.character(block[["border_black"]])))
    )
  }
  paste0("{", paste(parts, collapse = ","), "}")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"map":%s,"heatmap":%s,"scatter":%s,"spine":%s,"bar":%s,',
    '"pie":%s,"perspective":%s,"mosaic":%s,"lines":%s,',
    '"perspective_single":%s,"median_ms":%.17g}\n'
  ),
  block_json(value$map),
  block_json(value$heatmap),
  block_json(value$scatter),
  block_json(value$spine),
  block_json(value$bar),
  block_json(value$pie),
  block_json(value$perspective),
  block_json(value$mosaic),
  block_json(value$lines),
  block_json(value$perspective_single),
  median(elapsed) * 1000
))
