import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "lscvplot"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("lscvplot-py.py", "_plot-py-common.py"))
