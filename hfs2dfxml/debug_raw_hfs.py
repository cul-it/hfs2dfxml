import hfs2dfxml as hfs2dfxml
import subprocess
import Objects as DFXML

# NOTE For those who are adventurous...
# This script is meant to debug (from raw hfsutils output)
# When you don't have the actual disk image to check against

# Read in raw hfsutils output
with open('DEBUG_hfs2dfxml.txt', 'r') as dbg:
    dbg = dbg.read().decode('unicode-escape').encode('macroman')
    dbg = dbg.strip('\n') # Remove last erroneous linebreak in debug file
    dbg_volobj = DFXML.VolumeObject()
    dbg_volobj.ftype_str = 'HFS'
    dbg_volobj.block_size = None
    dbg_volobj.block_count = None
    # NOTE Using same input for Creation and Modification times
    dbg_moddict = hfs2dfxml._parse_hls_mod(dbg)
    dbg_linedicts = hfs2dfxml._parse_hls_cre(dbg, dbg_moddict, False)
    for dbg_linedict in dbg_linedicts:
        dbg_volobj.append(hfs2dfxml._line_to_dfxml(dbg_linedict))
    DFXML_root = DFXML.DFXMLObject(version='1.0', dc={'type': 'Disk Image'})
    DFXML_root.append(dbg_volobj)
    with open('DEBUG_Output.xml', 'w') as dbgout:
        dbgout.write(DFXML_root.to_dfxml())
    subprocess.check_output(['xmllint', '--format', 'DEBUG_Output.xml',
                            '--output', 'DEBUG_Output.xml'])
