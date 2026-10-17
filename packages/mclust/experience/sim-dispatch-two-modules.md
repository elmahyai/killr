# Sim dispatch is split across two modules

- `mclust/sim.py` (`sim`) holds the group-A sim functions: E, V, EII, EEI, VEI, EVI, EEE, EEV.
- `mclust/simulate_mclust.py` (`_TRANSLATED`) holds the group-B sim functions: VEV, VII, VVI, VVV, EVV, VEE, EVE, VVE.
- `simulate_Mclust` and `simulate_densityMclust` check the name, then try `_TRANSLATED` and fall back to `mclust.sim.sim`. A model in neither table raises `NotImplementedError`.
- The two groups return different `SimMatrix` classes. Group B (`_sim_common`) stores the R attribute as `modelName`. Group A (`_sim_core`) stores it as `model_name`. Code that reads the attribute must accept both.
