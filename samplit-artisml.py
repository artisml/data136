import random
import sys
for i in open(sys.argv[1]):
    if random.random() < 0.01:
        print(i, end="")





