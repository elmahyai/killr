import sys, time, statistics
sys.path.insert(0, "packages/snakecase")
from snakecase.caseconverters import to_any_case
x = ["this Is a Strange_string", "AND THIS ANOTHER_One", "RRRStudio.V11", "species42value 23month 7-8", "", None]
def run(): return to_any_case(x)
value = run()
print("value")
print(repr(value))
untimed = run()
t=[]
for _ in range(20):
    a=time.perf_counter(); run(); t.append((time.perf_counter()-a)*1000)
print("translated_ms=" + repr(statistics.median(t)))
