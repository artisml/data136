import random
import sys

for CHANGEB in open(sys.argv[1]):
    if random.random() < 0.01:
        print(CHANGEB, end="")


