import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atf.driver import main
sys.exit(main(["atf"] + sys.argv[1:]))
