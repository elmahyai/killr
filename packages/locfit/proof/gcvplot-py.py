import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "gcvplot"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("gcvplot-py.py", "_plot-py-common.py"))
