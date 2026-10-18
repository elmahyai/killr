# Axis tick sequences

The labeling package's algorithms return numeric tick locations, not plot
objects. R's `seq` can preserve an endpoint with floating-point arithmetic,
so translated tick generators should construct the same arithmetic progression
rather than round labels for display.
