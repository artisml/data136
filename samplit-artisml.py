import random
import sys
for CHANGEA in open(sys.argv[1]):
    if random.random() < 0.01:
        print(CHANGEA, end="")






