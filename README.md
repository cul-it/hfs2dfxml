# hfs2dfxml
Utility to parse hfsutils output and produce DFXML for HFS-formatted disk images

## System Requirements:
* `hfsutils` (http://www.mars.org/home/rob/proj/hfs; or installed via your distribution's package manager)
* `python-magic`
* Python DFXML Bindings (http://github.org/simsong/dfxml)
* DFXML Schema (http://github.org/dfxml-working-group/dfxml-schema) for testing and validation of results
* `xmllint` for validation (in tests) and pretty-printing DFXML output.

## Setup and configuration
* Install `hfsutils` and `python-magic`
* `hfs2dfxml.py` - Specify path for Python DFXML Bindings in script
* `hfs2dfxml_tests.py` - Specify path for image file in script to run tests

## BitCurator directions
The following directions were tested on BitCurator 1.5.11. The following installation/configuration steps require the Terminal.
* `which xmllint` - Output should be `/usr/bin/xmllint`
* `which git` - Output should be `/usr/bin/git`
* `sudo apt-get install hfsutils`
* `which hmount` - Output should be `/usr/local/bin/hmount` or `/usr/bin/hmount`. (If this doesn't work, installation of hfsutils may have failed.)
* `sudo apt-get install python-magic`
* `cd ~/Desktop`
* `git clone https://github.com/cul-it/hfs2dfxml`
* `cd hfs2dfxml/hfs2dfxml`
* `git clone https://github.com/simsong/dfxml/`
* `cd ../tests`
* `git clone https://github.com/dfxml-working-group/dfxml_schema`

## How to use
To generate DFXML for an HFS-formatted volume, navigate to the hfs2dfxml directory and use:

`python hfs2dfxml.py [HFS volume] [output file]`

Note: [output file] must not already exist.

Optionally, place hfs2dfxml in your Python path and import it in your own code to call `hfs_volobj`. This function returns a standalone DFXML Volume object.

## Known limitations (and implied to do list)
* HFS namespace is projected and not yet officially part of the DFXML schema. See: [https://github.com/dfxml-working-group/dfxml_schema/issues/23]
* Byte runs not reported for fileobjects
* Timestamps only include day/month/year and not specific time
* Tested on CD-ROM disc image of HFS volume only; submissions of additional HFS volumes to do further testing will be happily accepted
If you encounter a bug or issue not listed above, please feel free to file an issue in GitHub

### Contact
dd388 AT cornell DOT edu

### Thank you
Alex Nelson, Kate Tasker
