import runpy, sys, os
os.environ["PLOT_PROOF_NAME"] = "panel.xyplot.lf"
sys.argv[0] = __file__
runpy.run_path(__file__.replace("panel.xyplot.lf-py.py", "_plot-py-common.py"))
