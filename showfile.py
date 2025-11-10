##
## Micropython/Circuitpython helper to display a file
##

def show_file(fname):
    with open(fname) as f:
        for line in f:
            print line
