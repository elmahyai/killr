.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({library(nlme); library(lattice)})

# Writes the values R's plot.lme plots for the Orthodont fit: the x (fitted),
# the y (Pearson residuals), the group of each row, and the axis labels.
# The Python proof reads these, since lme is not translated yet.
fit <- lme(distance ~ age, data = Orthodont, control = lmeControl(apVar = FALSE))
p <- plot(fit)
pa <- p$panel.args[[1]]
groups <- as.character(getGroups(fit))
stopifnot(identical(groups, as.character(names(fitted(fit)))))
out <- data.frame(
  fitted = as.numeric(pa$x),
  pearson = as.numeric(pa$y),
  group = groups,
  stringsAsFactors = FALSE
)
write.csv(out, "proof/data/plot-lme-orthodont.csv", row.names = FALSE)
labels <- list(xlab = p$xlab, ylab = p$ylab)
writeLines(
  sprintf('{"xlab": "%s", "ylab": "%s"}', labels$xlab, labels$ylab),
  "proof/data/plot-lme-orthodont.json"
)
