import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "aicplot"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("aicplot-py.py", "_plot-py-common.py"))
