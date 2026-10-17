"""Translation of sass::as_sass_layer().

R calls sass_bundle(x)$layers and then plucks each layer field. Plucking keeps
every non-NULL value as a list, except html_deps and file_attachments, which
are concatenated one level. defaults is plucked from the layers in reverse.
"""

from ._common import SassLayer
from ._common import SassBundle
from ._sass_values import layers_of


def _has_any_name_recursive(x) -> bool:
    if isinstance(x, dict):
        if any(k for k in x):
            return True
        return any(_has_any_name_recursive(v) for v in x.values())
    if isinstance(x, list):
        return any(_has_any_name_recursive(v) for v in x)
    return False


def sass_bundle_layers(x) -> list:
    """R sass_bundle(x)$layers for one unnamed argument."""
    if x is None:
        return []
    if isinstance(x, SassBundle):
        return layers_of(x)
    if isinstance(x, SassLayer):
        return [x]
    if _has_any_name_recursive(x):
        return [SassLayer(defaults=x, file_attachments=[])]
    return [SassLayer(rules=x, file_attachments=[])]


def _pluck(layers, key, unlist=False):
    res = [getattr(layer, key) for layer in layers]
    res = [v for v in res if v is not None]
    if not res:
        return None
    if not unlist:
        return res
    merged_dict = {}
    merged_list = []
    for v in res:
        if isinstance(v, dict):
            merged_dict.update(v)
        elif isinstance(v, (list, tuple)):
            merged_list.extend(v)
        else:
            merged_list.append(v)
    if merged_dict and not merged_list:
        return merged_dict
    return merged_list


def as_sass_layer(x):
    if isinstance(x, SassLayer):
        return x
    if x is None:
        # R: rlang::set_names(NULL, NULL) fails on the NULL layer list.
        raise ValueError("`x` must be a vector")
    layers = sass_bundle_layers(x)
    return SassLayer(
        functions=_pluck(layers, "functions"),
        defaults=_pluck(list(reversed(layers)), "defaults"),
        mixins=_pluck(layers, "mixins"),
        rules=_pluck(layers, "rules"),
        declarations=_pluck(layers, "declarations"),
        html_deps=_pluck(layers, "html_deps", unlist=True),
        file_attachments=_pluck(layers, "file_attachments", unlist=True),
    )
