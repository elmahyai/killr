import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "panel.locfit"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("panel.locfit-py.py", "_plot-py-common.py"))
