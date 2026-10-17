import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "plotbyfactor"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("plotbyfactor-py.py", "_plot-py-common.py"))
