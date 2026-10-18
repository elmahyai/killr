"""Missing-value and label helpers for the labelled translation batch."""
from __future__ import annotations
import copy, math
from dataclasses import dataclass, field

@dataclass(frozen=True)
class TaggedNA:
    tag: str = ""

@dataclass
class LabelledVector:
    values: list
    labels: dict = field(default_factory=dict)
    label: str | None = None
    na_values: list | None = None
    na_range: list | None = None
    attributes: dict = field(default_factory=dict)
    def copy(self): return copy.deepcopy(self)

def _nan(x): return isinstance(x, float) and math.isnan(x)
def _eq(a,b): return (isinstance(a,TaggedNA) and isinstance(b,TaggedNA) and a.tag==b.tag) or (_nan(a) and _nan(b)) or a==b
def _has(xs,x): return any(_eq(v,x) for v in xs)
def _mask(x):
    out=[]
    for v in x.values:
        hit=x.na_values is not None and _has(x.na_values,v)
        if x.na_range is not None and v is not None and not _nan(v) and not isinstance(v,TaggedNA):
            try: hit=hit or x.na_range[0] <= v <= x.na_range[1]
            except TypeError: pass
        out.append(bool(hit) and v is not None and not _nan(v) and not isinstance(v,TaggedNA))
    return out

def is_user_na(x): return _mask(x)
def is_regular_na(x): return [(v is None or _nan(v)) and not u and not isinstance(v,TaggedNA) for v,u in zip(x.values,_mask(x))]
def na_values(x): return copy.deepcopy(x.na_values) if isinstance(x,LabelledVector) else None
def na_range(x): return copy.deepcopy(x.na_range) if isinstance(x,LabelledVector) else None
def set_na_values(x,*values,_values=None,**kw):
    if isinstance(x,LabelledVector):
        y=x.copy(); y.na_values=list(values) if _values is None else _values; return y
    return x
def set_na_range(x,*values,_values=None,**kw):
    if isinstance(x,LabelledVector):
        y=x.copy(); y.na_range=list(values) if _values is None else _values; return y
    return x
def _clear(x,to_na=False,to_tagged=False):
    y=x.copy(); m=_mask(y)
    if to_tagged:
        vals=sorted({repr(v):v for v,h in zip(y.values,m) if h}.values(),key=repr)
        if len(vals)<=26:
            mp={repr(v):TaggedNA(chr(97+i)) for i,v in enumerate(vals)}
            y.values=[mp.get(repr(v),v) if h else v for v,h in zip(y.values,m)]
            y.labels={k:mp.get(repr(v),v) for k,v in y.labels.items()}
        else: to_na=True
    if to_na:
        bad={repr(v) for v,h in zip(y.values,m) if h}
        y.values=[None if h else v for v,h in zip(y.values,m)]
        y.labels={k:v for k,v in y.labels.items() if repr(v) not in bad}
    y.na_values=None; y.na_range=None; return y
def user_na_to_na(x): return _clear(x,to_na=True) if isinstance(x,LabelledVector) else x
def user_na_to_tagged_na(x): return _clear(x,to_tagged=True) if isinstance(x,LabelledVector) else x
def remove_user_na(x,user_na_to_na=False,user_na_to_tagged_na=False):
    return _clear(x,user_na_to_na,user_na_to_tagged_na) if isinstance(x,LabelledVector) else x
def recode_if(x,condition,true):
    y=x.copy() if isinstance(x,LabelledVector) else list(x); vals=y.values if isinstance(y,LabelledVector) else y
    if len(vals)!=len(condition) or (len(true)!=1 and len(true)!=len(vals)): raise ValueError("length mismatch")
    for i,c in enumerate(condition):
        if c is True: vals[i]=true[0] if len(true)==1 else true[i]
    return y
def remove_attributes(x,attributes):
    y=x.copy() if isinstance(x,LabelledVector) else x
    if isinstance(y,LabelledVector):
        for a in attributes:
            if a in ("label","var_label"): y.label=None
            elif hasattr(y,a): setattr(y,a,None)
            else: y.attributes.pop(a,None)
    return y
def remove_var_label(x):
    return remove_attributes(x,["label"])
def remove_val_labels(x):
    y=x.copy() if isinstance(x,LabelledVector) else x
    if isinstance(y,LabelledVector): y.labels={}
    return y
def remove_labels(x,user_na_to_na=False,keep_var_label=False,user_na_to_tagged_na=False):
    y=remove_user_na(x,user_na_to_na,user_na_to_tagged_na) if isinstance(x,LabelledVector) else x
    if isinstance(y,LabelledVector):
        if not keep_var_label: y.label=None
        y.labels={}; y.attributes.pop("format.spss",None)
    return y
