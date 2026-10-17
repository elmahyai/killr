from ._common import layer, bundle


def sass_layer(functions=None, defaults=None, mixins=None, rules=None,
               html_deps=None, file_attachments=None, declarations=None,
               tags=None):
    del tags  # deprecated in R; retained for call compatibility
    return bundle(layer(functions=functions, defaults=defaults, mixins=mixins,
                        rules=rules, html_deps=html_deps,
                        file_attachments=file_attachments or {},
                        declarations=declarations))
