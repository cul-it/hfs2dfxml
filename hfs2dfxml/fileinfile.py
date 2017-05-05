"""
Source code put in public domain by Didier Stevens, no Copyright
On GitHub: https://github.com/DidierStevens/DidierStevensSuite/blob/master/find-file-in-file.py
Modified from version 1: https://didierstevens.com/files/software/find-file-in-file_v0_0_1.zip

"""

import operator

def File2Strings(filename):
    try:
        f = open(filename, 'rb')
    except:
        return None
    try:
        return f.read()
    except:
        return None
    finally:
        f.close()

def Match(contained, containing, index, dFound):
    for i in range(len(contained)):
        if i + index >= len(containing) or contained[i] != containing[i + index] or i + index in dFound:
            return i
    return len(contained)

def ScanSub(contained, containing, dFound):
    dMatches = {}
    index = 0
    while True:
        result = containing.find(contained[0:10], index)
        if result == -1:
            break
        found = Match(contained, containing, result, dFound)
        if found > 0:
            dMatches[result] = found
        index = result + 1
    if dMatches == {}:
        return None, None
    return max(dMatches.items(), key=operator.itemgetter(1))

def Scan(contained, containing):
    dFound = {}
    byteruns = []
    remaining = contained
    while True:
        index, length = ScanSub(remaining, containing, dFound)
        if index == None:
            break
        byterun = (index, length)
        byteruns.append(byterun)
#        print('%08x %08x (%d%%)' % (index, length, length * 100.0 / len(contained)))
        for counter in range(length):
            dFound[counter + index] = True
        remaining = remaining[length:]
        if len(remaining) == 0:
            break
        if len(remaining) < 10:
            break
    return byteruns

def FindFileInFile(fileContained, fileContaining):
    # Clean this up
    contained = File2Strings(fileContained)
    if contained == None:
        return False
    if len(contained) < 10:
        return False
    containing = File2Strings(fileContaining)
    if containing == None:
        return False
    if len(containing) < 10:
        return False
    br = Scan(contained, containing)
    return br

