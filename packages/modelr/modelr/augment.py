"""Add predictions or residuals to a data frame."""

from __future__ import annotations

from modelr.design import predict, residuals
from modelr.frame import Factor, Frame, as_frame


def add_predictions(data, model, var="pred", type=None):
    frame = as_frame(data)
    return frame.with_column(var, predict(model, frame, type=type))


def spread_predictions(data, type=None, **models):
    frame = as_frame(data)
    for name, model in models.items():
        frame = frame.with_column(name, predict(model, frame, type=type))
    return frame


def gather_predictions(data, pred="pred", model_name="model", type=None, **models):
    frames = [add_predictions(data, model, var=pred, type=type) for model in models.values()]
    return _rbind(frames, list(models), model_name)


def add_residuals(data, model, var="resid"):
    frame = as_frame(data)
    return frame.with_column(var, residuals(model, frame))


def spread_residuals(data, **models):
    frame = as_frame(data)
    for name, model in models.items():
        frame = frame.with_column(name, residuals(model, frame))
    return frame


def gather_residuals(data, resid="resid", model_name="model", **models):
    frames = [add_residuals(data, model, var=resid) for model in models.values()]
    return _rbind(frames, list(models), model_name)


def _rbind(frames, names, name_column):
    if not frames:
        return Frame({})
    order = [name_column, *frames[0].names()]
    columns = {name: [] for name in order}
    for name, frame in zip(names, frames):
        columns[name_column].extend([name] * frame.nrow)
        for column in frame.names():
            columns[column].extend(_values(frame.columns[column]))
    return Frame(columns)


def _values(column):
    if isinstance(column, Factor):
        return list(column.values)
    return list(column)
