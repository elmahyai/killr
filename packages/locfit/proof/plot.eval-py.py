import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "plot.eval"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("plot.eval-py.py", "_plot-py-common.py"))
