# hfs2dfxml
Utility to parse hfsutils output and produce DFXML for HFS-formatted disk images

## System Requirements:
* `hfsutils` (http://www.mars.org/home/rob/proj/hfs; or installed via your distribution's package manager)
* `python-magic`
* Python DFXML Bindings (http://github.org/simsong/dfxml)
* DFXML Schema (http://github.org/dfxml-working-group/dfxml-schema) for testing and validation of results

## Setup and configuration
* Install `hfsutils` and `python-magic`
* `hfs2dfxml.py` - Specify path for Python DFXML Bindings in script
* `hfs2dfxml_tests.py` - Specify path for image file in script to run tests

## How to use
To generate DFXML for an HFS-formatted volume, use:
`python hfs2dfxml.py [HFS volume] [output file]`

Optionally, place hfs2dfxml in your Python path and import it in your own code to call `hfs_volobj`. This function returns a standalone DFXML Volume object.

## Known limitations (and implied to do list)
* Byte runs not reported for fileobjects
* Timestamps only include day/month/year and not specific time
* Tested on CD-ROM disc image of HFS volume only; submissions of additional HFS volumes to do further testing will be happily accepted
If you encounter a bug or issue not listed above, please feel free to file an issue in GitHub

### Contact
dd388 AT cornell DOT edu
