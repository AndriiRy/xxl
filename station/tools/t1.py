import sys, os, shutil, time, json
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[1])
import web
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)
A = web.App(d, True); A.new_project("kuhnia")
t = time.time(); A.job_scan(); print("scan s", time.time() - t)
print("\n".join(A.log[-25:]))
