import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "cpplot"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("cpplot-py.py", "_plot-py-common.py"))
