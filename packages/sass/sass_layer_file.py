from ._common import bundle, read_layer_file


def sass_layer_file(file):
    return bundle(read_layer_file(file))
