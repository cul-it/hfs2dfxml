#!/usr/bin/env python
#
# hfs2dfxml parses hfsutils output into DFXML
# or produce DFXML Volume Object for HFS partition
#
# Requirements: hfsutils
#               python-magic
#               Python DFXML Bindings (specify path below)
#               DFXML Schema (for tests)

__version__ = '0.1.0'

import os
import sys
import subprocess
import re
import tempfile
import magic
import xml.etree.ElementTree as ET
from datetime import datetime
from hashlib import md5
from hashlib import sha1

# Import Python DFXML Bindings
sys.path.append('dfxml/python')
import Objects as DFXML


PATTERNFILE = re.compile('^(\d+)\s+(\w+)\s+(.{4}/.{4})\s+(\d+)\s+(\d+)\s+(\w{3}\s{1,2}\d{1,2}\s{1,2}\d{2}:{0,1}\d{2})\s(".*")(\**)$')
PATTERNDIR = re.compile('^(\d+)\s+(\w+)\s+(\d+\sitems*)\s+(\w{3}\s{1,2}\d{1,2}\s{1,2}\d{2}:{0,1}\d{2})\s(".*"):$')

DEBUG = False

def _reformat_date(unformatted):
    # Reformats dates found in hls output for comparisons.
    reformat = unformatted.replace('  ', ' ')
    reformat = datetime.strptime(reformat, '%b %d %Y')
    return reformat


def _call_humount(report_err=False):
    # Calls humount; optionally reports any errors (e.g., volume is
    # already mounted).
    try:
        subprocess.check_call(['humount'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if report_err:
            print('_call_humount error: {0}'.format(e.output))


def _call_hmount(hfsfilename):
    # Calls hmount with path to HFS volume. Returns output of command,
    # which includes volume name and other information.
    try:
        hmount_output = subprocess.check_output(['hmount', hfsfilename],
                                                stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        sys.exit('_call_hmount error: {0}'.format(e.output,))
    return hmount_output


def _call_hls():
    # Calls hls twice to obtain output for generating fileobjects
    # Returns output of command unformatted.
    try:
        # NOTE: hls arguments (from man page)
        # The order listed is to ensure consistent formatting for parsing.
        # -1 Output is formatted so entry appears on a single line.
        # -a All files and directories and "invisible" files are shown.
        # -c Sort and display by creation date (hls_cre_output only)
        # -m Sort and display by modification date (hls_mod_output only)
        # -i Show catalog IDs for each entry.
        # -l Display entries in long format, including entry type,
        #    flags, file type and reator, resource bytes, data bytes,
        #    date of creation or modification, and pathname.
        # -Q Cause all filenames to be enclosed in double-quotes and
        #    special/non-printable characters to be properly escaped.
        # -R Recursively descent into and display each directory contents.
        # -U Do not sort directory contents
        # -F Cause certain output filenames to be followed by
        #    a single-character flag (e.g., colon for directories and
        #    asterisk for applications.
        # -N Cause all filenames to be output verbatim without any
        #    escaping or question mark substitution.
        hls_cre_output = subprocess.check_output(['hls', '-1acilQRUFN'])
        hls_mod_output = subprocess.check_output(['hls', '-1amilQRUFN'])
    except subprocess.CalledProcessError as e:
        sys.exit('_call_hls error: {0}'.format(e.output,))
    if DEBUG:
        with open('DEBUG_hfs2dfxml.txt', 'w') as debugfile:
            _debug_output = hls_cre_output.split('\n')
            for dbg in _debug_output:
                debugfile.write(dbg.decode('macroman').encode('unicode-escape'))
                debugfile.write('\n')
    return (hls_cre_output, hls_mod_output)


def _parse_hls_mod(hls_mod_raw):
    # Takes raw hls input (assumes file modification times).
    # Returns a dictionary to correlate with additional hls output.
    hls_mod_dict = {}
    hls_mod_raw = hls_mod_raw.split('\n')
    for hls_mod_line in hls_mod_raw:
        if hls_mod_line.startswith(':'):
            continue
        elif hls_mod_line == '\n':
            continue
        elif hls_mod_line == '':
            continue

        hls_mod_line = hls_mod_line.strip()
        parse_file_mod = re.match(PATTERNFILE, hls_mod_line)
        parse_dir_mod = re.match(PATTERNDIR, hls_mod_line)

        if parse_file_mod and not parse_dir_mod:
            mod_cnid = parse_file_mod.group(1)
            mod_mdate = parse_file_mod.group(6)
            mod_filename = parse_file_mod.group(7)
            mod_nametype = parse_file_mod.group(2)
        elif not parse_file_mod and parse_dir_mod:
            mod_cnid = parse_dir_mod.group(1)
            mod_mdate = parse_dir_mod.group(4)
            mod_filename = parse_dir_mod.group(5)
            mod_nametype = parse_dir_mod.group(2)
        else:
            sys.exit('_parse_hls_mod error: Unexpected line format.\n' +
                     '|{0}|'.format(hls_mod_line))

        if mod_cnid in hls_mod_dict:
            sys.exit('_parse_hls_mod error: Duplcate CNID found.\n' +
                     '|{0}|'.format(hls_mod_line))
        else:
            hls_mod_dict[mod_cnid] = (mod_mdate,
                                      mod_filename.decode('macroman'))
    return hls_mod_dict


def _file_line(regex_file_cre):
    # Takes regular expression matching entry for file in hls output.
    # Returns dictionary with formatted values corresponding to DFXML tags.
    HFS_file_line = {}
    HFS_file_line['cnid'] = regex_file_cre.group(1)
    HFS_file_line['HFSrsrcsize'] = regex_file_cre.group(4)
    HFS_file_line['filesize'] = regex_file_cre.group(5)

    if regex_file_cre.group(2).startswith('f'):
        HFS_file_line['name_type'] = 'r'
    elif regex_file_cre.group(2).startswith('F'):
        HFS_file_line['name_type'] = 'r'
        HFS_file_line['HFSlocked'] = '1'
    else:
        sys.exit('_file_line error: Unexpected Entry Type.\n' +
                 '{0}'.format(regex_file_cre.groups()))
    if regex_file_cre.group(2).endswith('i'):
        HFS_file_line['HFSflags'] = 'i'

    if ((regex_file_cre.group(3) != '    /    ') and
       (regex_file_cre.group(3) != '????/????')):
        _HFStype_creator = regex_file_cre.group(3).decode('macroman')
        HFS_file_line['HFStype_creator'] = _HFStype_creator.encode(
                                           'unicode-escape')
    _crtime = _reformat_date(regex_file_cre.group(6))
    if _crtime != datetime(1904, 1, 1):
        HFS_file_line['crtime'] = _crtime

    HFS_file_line['_filename'] = regex_file_cre.group(7).decode('macroman')
    return HFS_file_line


def _hcopy_res(hfs_filepath):
    # Takes full path of hfs file.
    # Returns strings for libmagic, md5 and sha1 hash of file.
    # NOTE: This copies the output of hcopy to a temporary file.
    # NOTE: This only runs on data fork of specified file. (hcopy -r)
    with tempfile.NamedTemporaryFile(delete=False) as tmp_fileout:
        tmp_fileout.write(subprocess.check_output(['hcopy', '-r',
                                                  r'{0}'.format(
                                                   hfs_filepath,), '-']))
        tmp_fileout.close()
        _libmagic = magic.open(magic.MAGIC_NONE)
        _libmagic.load()
        libmagic = _libmagic.file(tmp_fileout.name)
        _libmagic.close()
        _hasher_md5 = md5()
        _hasher_sha1 = sha1()
        with open(tmp_fileout.name, 'rb') as tmp_hash:
            buf = tmp_hash.read(128)
            while len(buf) > 0:
                _hasher_md5.update(buf)
                _hasher_sha1.update(buf)
                buf = tmp_hash.read(128)
        file_md5 = _hasher_md5.hexdigest()
        file_sha1 = _hasher_sha1.hexdigest()
        os.unlink(tmp_fileout.name)
        return libmagic, file_md5, file_sha1


def _dir_line(regex_dir_cre):
    # Takes regular expression matching entry for directory in hls output.
    # Returns dictionary with formatted values corresponding to DFXML tags.
    HFS_dir_line = {}
    HFS_dir_line['cnid'] = regex_dir_cre.group(1)
    if regex_dir_cre.group(2).startswith('d'):
        HFS_dir_line['name_type'] = 'd'  # TODO: Need test for locked dirs.
    elif regex_dir_cre.group(2).startswith('D'):
        HFS_dir_line['name_type'] = 'd'
        HFS_dir_line['HFSlocked'] = '1'
    else:
        sys.exit('_dir_line error: Unexpected entry type.\n' +
                 '{0}'.format(regex_dir_cre.groups()))
    if regex_dir_cre.group(2).endswith('i'):
        HFS_dir_line['HFSflags'] = 'i'
    _crtime = _reformat_date(regex_dir_cre.group(4))
    if _crtime != datetime(1904, 1, 1):
        HFS_dir_line['crtime'] = _crtime
    HFS_dir_line['_dirname'] = regex_dir_cre.group(5).decode('macroman')
    return HFS_dir_line


def _line_to_dfxml(hfs_line):
    # Takes in dictionary with properties of HFS file or directory
    # Returns DFXML FileObject with appropriate values assigned.
    # NOTE: hfsutils output does not include deleted files.
    this_fileobj = DFXML.FileObject()
    this_fileobj.inode = hfs_line['cnid']
    this_fileobj.name_type = hfs_line['name_type']
    this_fileobj.alloc = '1'
    if hfs_line.get('filename') is not None:
        this_fileobj.filename = hfs_line['filename']
        this_fileobj.filesize = hfs_line['filesize']
    else:
        this_fileobj.filename = hfs_line['dirname']
    if hfs_line.get('libmagic') is not None:
        this_fileobj.libmagic = hfs_line['libmagic']
        this_fileobj.md5 = hfs_line['md5']
        this_fileobj.sha1 = hfs_line['sha1']
    if hfs_line.get('crtime') is not None:
        this_fileobj.crtime = hfs_line['crtime'].isoformat()
    if hfs_line.get('mtime') is not None:
        this_fileobj.mtime = hfs_line['mtime'].isoformat()
    # NOTE: The following values are in the projected HFS namespace.
    # See: https://github.com/dfxml-working-group/dfxml_schema/issues/23
    HFS_namespace_elems = DFXML.OtherNSElementList()
    if hfs_line.get('HFStype_creator') is not None:
        _HFStype_creator = ET.Element('{http://www.forensicswiki.org/' +
                                      'wiki/HFS}HFStype_creator')
        _HFStype_creator.text = hfs_line['HFStype_creator']
        HFS_namespace_elems.append(_HFStype_creator)
    if hfs_line.get('HFSrsrcsize') is not None:
        _HFSrsrcsize = ET.Element('{http://www.forensicswiki.org/' +
                                  'wiki/HFS}HFSrsrcsize')
        _HFSrsrcsize.text = hfs_line['HFSrsrcsize']
        HFS_namespace_elems.append(_HFSrsrcsize)
    if hfs_line.get('HFSlocked') is not None:
        _HFSlocked = ET.Element('{http://www.forensicswiki.org/' +
                                'wiki/HFS}HFSlocked')
        _HFSlocked.text = hfs_line['HFSlocked']
        HFS_namespace_elems.append(_HFSlocked)
    if hfs_line.get('HFSflags') is not None:
        _HFSflags = ET.Element('{http://www.forensicswiki.org/' +
                               'wiki/HFS}HFSflags')
        _HFSflags.text = hfs_line['HFSflags']
        HFS_namespace_elems.append(_HFSflags)
    this_fileobj.externals = (HFS_namespace_elems)
    return this_fileobj


def _parse_hls_cre(hls_cre_raw, hls_mod_dict, hcopy=True):
    # Takes in raw hls output with creation times and dict with mod times
    # Returns list of dictionaries with HFS data
    hfs_all_files = []
    hls_cre_sections = hls_cre_raw.split('\n\n')
    hls_cre_sections = [hlstmp.split('\n') for hlstmp in hls_cre_sections]
    _standalone_dir_id = re.compile(':(.*):')

    for hls_cre_block in enumerate(hls_cre_sections):
        this_dir = False
        for hls_cre_entry in enumerate(hls_cre_block[1]):
            # First line in section has directory name
            if ((hls_cre_entry[0] == 0) and (hls_cre_block[0] > 0)):
                _dirname = re.match(_standalone_dir_id, hls_cre_entry[1])
                if not _dirname:
                    sys.exit('_parse_hls_cre error: Directory not found ' +
                             'on first line of section.\n' +
                             '|{0}|'.format(hls_cre_entry[1]))
                else:
                    this_dir = _dirname.group(1)
            else:
                if hls_cre_entry[1] == '':
                    continue  # Skip blank line
                if hls_cre_block[0] == 0:
                    this_dir = ''  # Root is :
                if this_dir is False:
                    sys.exit('_parse_hls_cre error: this_dir was not ' +
                             'already assigned.\n')
                hls_cre_entry_line = hls_cre_entry[1].strip()
                parse_file_cre = re.match(PATTERNFILE, hls_cre_entry_line)
                parse_dir_cre = re.match(PATTERNDIR, hls_cre_entry_line)
                if ((parse_file_cre) and not(parse_dir_cre)):
                    this_line = _file_line(parse_file_cre)
                    _cnid = this_line['cnid']
                    _filename = this_line['_filename']
                    _mod_date, _fname_verify = hls_mod_dict[_cnid]

                    if _fname_verify == _filename:
                        _mod_date = _reformat_date(_mod_date)
                        if _mod_date != datetime(1904, 1, 1):
                            this_line['mtime'] = _mod_date
                    else:
                        sys.exit('_parse_hls_cre error: Inode/filename' +
                                 'mismatch when retrieving modification' +
                                 'time.\n' +
                                 '|{0}|{1}|'.format(_fname_verify,
                                                    _filename))
                    _filename = _filename.strip('"')
                    _filename = _filename.encode('unicode-escape')
                    if this_dir != '':
                        this_line['filename'] = ':{0}:{1}'.format(
                                                    this_dir, _filename)
                    else:
                        this_line['filename'] = ':{0}'.format(
                                                            _filename)
                    if hcopy and this_line['filesize'] != '0':
                        _hcopy_name = this_line['filename'].decode(
                                                'unicode-escape').encode(
                                                'ascii', 'replace')
                        this_line['libmagic'], this_line['md5'], \
                        this_line['sha1'] = _hcopy_res(_hcopy_name)
                    # NOTE: To revert filename back to "original":
                    # this_line['filename'].decode('unicode-escape')

                elif (not(parse_file_cre) and parse_dir_cre):
                    this_line = _dir_line(parse_dir_cre)
                    _cnid = this_line['cnid']
                    _dirname = this_line['_dirname']
                    _mod_date, _dname_verify = hls_mod_dict[_cnid]

                    if _dname_verify == _dirname:
                        _mod_date = _reformat_date(_mod_date)
                        if _mod_date != datetime(1904, 1, 1):
                            this_line['mtime'] = _mod_date
                    else:
                        sys.exit('_parse_hls_cre error: Inode/filename ' +
                                 'mismatch when retrieving modification ' +
                                 'time.\n' +
                                 '|{0}|{1}|'.format(_dname_verify,
                                                    _dirname))
                    _dirname = _dirname.strip('"')
                    _dirname = _dirname.encode('unicode-escape')
                    if this_dir != '':
                        this_line['dirname'] = ':{0}:{1}'.format(this_dir,
                                                                 _dirname)
                    else:
                        this_line['dirname'] = ':{0}'.format(_dirname)
                else:
                    sys.exit('_parse_hls_cre error: File/dir mismatch.')
                hfs_all_files.append(this_line)
    return hfs_all_files


def hfs_volobj(hfs_filename):
    this_volobj = DFXML.VolumeObject()
    this_volobj.ftype_str = 'HFS'
    _volmagic = magic.open(magic.MAGIC_NONE)
    _volmagic.load()
    _volstring = _volmagic.file(hfs_filename)
    _volmagic.close()
    # NOTE: Need more testing with different HFS disk images
    if _volstring.startswith('Apple Driver Map'):
        _block_size, _block_count = re.search('blocksize (\d+), ' +
                                              'blockcount (\d+)',
                                              _volstring).groups()
    elif _volstring.startswith('Macintosh HFS data'):
        _block_size, _block_count = re.search('block size: (\d+), ' +
                                              'number of blocks: (\d+)',
                                              _volstring).groups()
    else:
        _block_size = None
        _block_count = None
    this_volobj.block_size = _block_size
    this_volobj.block_count = _block_count
    hfs_fileinfo = _call_hmount(hfs_filename)
    hlscre, hlsmod = _call_hls()
    hlsmoddict = _parse_hls_mod(hlsmod)
    linedicts = _parse_hls_cre(hlscre, hlsmoddict)
    for linedict in linedicts:
        this_volobj.append(_line_to_dfxml(linedict))
    _call_humount(report_err=True)  # Report if HFS file did not unmount
    return this_volobj


def hfs2dfxml(hfs_file):
    _call_humount()  # Ensure no other volume mounted by hfsutils
    ET.register_namespace('hfs', 'http://www.forensicswiki.org/wiki/HFS')
    DFXML_root = DFXML.DFXMLObject(version='1.0',
                                   dc={'type': 'Disk Image'})
    DFXML_root.sources = [os.path.basename(hfs_file)]
    DFXML_root.append(hfs_volobj(hfs_file))
    return DFXML_root


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Usage: python hfs2dfxml.py [HFS volume] [output file]')
    if os.path.isfile(sys.argv[1]):
        hfs = sys.argv[1]
        if os.path.isfile(sys.argv[2]):
            sys.exit('hfs2dfxml error: Output file already exists.')
        else:
            dfxml = sys.argv[2]
    else:
        sys.exit('hfs2dfxml error: HFS Volume not found.')
    with open(dfxml, 'w') as dfxmloutput:
        dfxmloutput.write(hfs2dfxml(hfs).to_dfxml())
    # NOTE: Comment out line below if pretty-printing XML isn't needed    
    subprocess.check_output(['xmllint', '--format', dfxml,
                             '--output', dfxml])
