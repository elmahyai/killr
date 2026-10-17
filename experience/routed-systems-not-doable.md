# Routed systems are not doable

A function can have `translated` false, an empty `blocked_by`, an empty `assigned`, and a `not_done` that does not begin with `Left`, and still not be doable. In colorspace, the 40 functions `scale_color_*`, `scale_colour_*`, and `scale_fill_*` (ggplot2 scales) and `hcl_color_picker`, `hcl_wizard`, `hclcolorpicker`, and `hclwizard` (Shiny apps) carry the `not_done` text "ggplot2 scale or Shiny app ... not translated". ggplot2 and shiny are listed in `cran/replaced.json`, so the chart and dashboard routes apply, not a numerical port.

Check `cran/replaced.json` and the Routing section of `CONSTITUTION.md` before translating a filtered function. Do not translate ggplot2 scales or Shiny apps as functions. Report them as routed, and do not write a 1e-8 proof for them.
