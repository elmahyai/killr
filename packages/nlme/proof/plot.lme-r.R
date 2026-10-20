.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(nlme); library(lattice)})

# Run from packages/nlme. The plotted values are read from the trellis object
# (panel.args) and from the plot.nls frame that holds abline, id and idLabels.
fit <- lme(distance ~ age, data = Orthodont, control = lmeControl(apVar = FALSE))

plotted <- function(p) {
  pa <- p$panel.args[[1]]
  frame <- environment(p$panel)
  list(
    x = as.numeric(pa$x),
    y = as.numeric(pa$y),
    panels = length(p$panel.args),
    abline = as.numeric(get("abl", frame)),
    id = get("id", frame),
    idLabels = get("idLabels", frame),
    xlab = p$xlab,
    ylab = p$ylab
  )
}

pdf(NULL)
default <- plotted(plot(fit))
labelled <- plotted(plot(fit, id = 0.05))
id_index <- which(labelled$id)
id_labels <- as.character(labelled$idLabels[id_index])

one <- function() print(plot(fit))
one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
invisible(dev.off())

svg("docs/output/plot.lme-r.svg", width = 7, height = 7)
print(plot(fit))
invisible(dev.off())
svg("docs/output/plot.lme-id-r.svg", width = 7, height = 7)
print(plot(fit, id = 0.05))
invisible(dev.off())

# The fitted values and Pearson residuals the object path reads, in row order.
fitted_values <- as.numeric(fitted(fit))
pearson <- as.numeric(resid(fit, type = "pearson"))
group_names <- as.character(getGroups(fit))

value <- c(default$x, default$y, default$abline)
value_id <- as.numeric(id_index)
cat(sprintf(
  "{\"value\":[%s],\"value_id\":[%s],\"id_labels\":[%s],\"labels\":{\"xlab\":\"%s\",\"ylab\":\"%s\"},\"panels\":%d,\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  paste(sprintf("%.17g", value_id), collapse = ","),
  paste(sprintf("\"%s\"", id_labels), collapse = ","),
  default$xlab,
  default$ylab,
  default$panels,
  median(elapsed) * 1000
))
cat(sprintf(
  "{\"fitted\":[%s],\"pearson\":[%s],\"group\":[%s]}\n",
  paste(sprintf("%.17g", fitted_values), collapse = ","),
  paste(sprintf("%.17g", pearson), collapse = ","),
  paste(sprintf("\"%s\"", group_names), collapse = ",")
))
