import sys
import hashlib
import subprocess
sys.path.append('../hfs2dfxml')
sys.path.append('../hfs2dfxml/dfxml/python')  # Python DFXML Bindings
import hfs2dfxml

# Specify path of test file
testimage=''

def hash_test_file():
    hasher_sha1 = hashlib.sha1()
    with open(testimage, 'rb') as tmp_hash:
        buf = tmp_hash.read(128)
        while len(buf) > 0:
            hasher_sha1.update(buf)
            buf = tmp_hash.read(128)
    return hasher_sha1

firsthash = hash_test_file()

with open('test_hfs2dfxml_output.xml', 'w') as dfxmloutput:
    dfxmloutput.write(hfs2dfxml.hfs2dfxml(testimage).to_dfxml())

secondhash = hash_test_file()

xmllint_res = subprocess.check_call(['xmllint', '--noout', '--schema',
                                     'dfxml_schema/dfxml.xsd',
                                     'test_hfs2dfxml_output.xml'])
if xmllint_res != 0:
    sys.exit('DFXML does not validate.')

if firsthash.hexdigest() == secondhash.hexdigest():
    print 'SHA1 match pre and post processing.'
else:
    sys.exit('SHA1 hashes do not match.')
