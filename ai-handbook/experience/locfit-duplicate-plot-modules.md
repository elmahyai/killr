# locfit duplicate plot modules

Pitfall seen in the locfit lcvplot proof.

- `packages/locfit/` holds two copies of `lcv.py` and `plotting.py`. The port is in the `locfit/` subfolder (`locfit/lcv.py`, `locfit/plotting.py`). The top-level copies are older and do not use the default tree path.
- A proof that imports `locfit_translated.plotting` gets the top-level copy. Its `lcv` leaves out the tree leave-one-out sum, so `lcvplot` was off by 1.41e-4 at alpha 0.8 while `df` matched exactly.
- Check which file a module name resolves to (`module.__file__`) before blaming the port. Load the `locfit/` subfolder as its own package (a `types.ModuleType` with `__path__` set) and alias the bare `locfit_raw` name, as `lcvplot-py.py` does.
- The fixed proof matches R to 4.4e-15 at alpha 0.4, 0.6 and 0.8.
