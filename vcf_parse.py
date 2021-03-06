#!/anaconda3/envs/python2/bin/python

"""
vcf_parse.py

Takes a VCF file and parses the variants to produce a tab delimited 
variant report.

Usage:  vcf_parse.py [-h] [-v] 
                     [-O OUTPUT]  
                     [-t TRANSCRIPTS] [-T TRANSCRIPT_STRICTNESS] 
                     [-b BED | -B BED_FOLDER] 
                     [-k KNOWN_VARIANTS]
                     [-c CONFIG] [-l] 
                     input
        vcf_parse.py -h for full description of options.

Author:     Erik Waskiewicz
Created:    31 Aug 2018
Version:    0.1.0
Updated:    31 Oct 2018
"""
__version__ = '0.1.0'
__updated__ = '31 Oct 2018'


import argparse
import logging
import textwrap

from scripts.vcf_report import vcf_report
from scripts.preferred_transcripts import preferred_transcripts
from scripts.bed_object import bed_object
from scripts.known_variants import known_variants


## -- PARSE INPUT ARGUMENTS -------------------------------------------

def get_args():
    """
    Use argparse package to take arguments from the command line. 
    See descriptions for full detail of each argument.
    """

    # Make argparse object, add description
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=textwrap.dedent(
        '''
        summary:
        Takes a VCF file and parses the variants to produce a tab delimited 
        variant report.
        '''
    ))


    # Version info
    parser.add_argument(
        '-v', '--version', action='version', 
        version=
            '%(prog)s\nversion:\t{}\nlast updated:\t{}'.format(
                __version__, __updated__
    ))


    # Arguments (see help string for full descriptions):
    # REQUIRED: VCF file input
    parser.add_argument(
        'input', action='store', 
        help='Filepath to input VCF file. REQUIRED.'
    )


    # OPTIONAL: Output folder, defaults to current directory if empty
    parser.add_argument(
        '-O', '--output', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to folder where output reports will be saved. 
        If missing, defaults to current directory.
        \n'''
    ))


    # OPTIONAL: List of preferred transcripts
    parser.add_argument(
        '-t', '--transcripts', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to preferred transcripts file. 

        Must be a tab seperated file with preferred transcripts in the second 
        column. If missing, all entries in the preferred transcript column 
        will be labelled as 'Unknown'.
        \n'''
    ))


    # OPTIONAL: Preferred transcripts strictness
    parser.add_argument(
        '-T', '--transcript_strictness', action='store', default='low', 
        help=textwrap.dedent(
        '''
        Strictness of matching while annotating preferred transcripts.
        Default setting is low.

        Options: 

        high - Transcripts must be an exact match. 
               e.g. NM_001007553.2 and NM_001007553.1 won't match,
                    NM_001007553.1 and NM_001007553.1 will.

        low  - Transcripts will match regardless of the version number. The 
               version number is after the . at the end of a transcript 
               e.g. NM_001007553.2 and NM_001007553.1 will match.
        \n'''
    ))


    # OPTIONAL: either a single BED file or a folder containing BED 
    # files, only one of these can be used
    bed_files = parser.add_mutually_exclusive_group()

    # Single BED file
    bed_files.add_argument(
        '-b', '--bed', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to a single BED file. 

        The BED file will be applied to the variant report and a seperate
        report saved with the BED file applied. This report will be saved in 
        the same output folder as the original variant report, with the BED 
        file name added to it.
        Cannot be used together with -B flag.
        \n'''
            ))

    # Multiple BED files
    bed_files.add_argument(
        '-B', '--bed_folder', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to folder containing BED files. 

        Each BED file will be applied to the variant report and a seperate
        report saved with the BED file applied. These reports will be saved in
        a new folder within the output folder, named the same as the input BED
        folder. 
        The file names will be the same as the original variant report, with 
        the BED file name added to them.
        Cannot be used together with -b flag.
        \n'''
    ))


    # OPTIONAL: File containing known variants
    parser.add_argument(
        '-k', '--known_variants', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to known variants file. 

        This is a VCF file containing any known variants and an associated 
        classification. The classification will be added to the variant 
        report. The VCF must have an annotation named 'Classification' within 
        the INFO field for each variant.

        Key:
        0 - Artifact
        1 - Benign
        2 - Likely benign
        3 - VUS
        4 - Likely pathogenic
        5 - Pathogenic
        \n'''
    ))


    # OPTIONAL: File containing the headers for the report
    parser.add_argument(
        '-c', '--config', action='store', 
        help=textwrap.dedent(
        '''
        Filepath to config file. 

        This is a tab seperated text file containing a number of rows, where 
        each row specifies an annotation to be included in the variant report.
        Only annotations included in the config file will be included in the
        variant report.
        The columns in the variant report will be in the same order as the 
        order in which the annotations appear in the config file.

        Each row contains:

        Column 1 - Required. Annotation headers, these must match up with how
                   they appear in the VCF (case sensitive).

        Column 2 - Required. Location where to find the data within the VCF, 
                   used to select the correct parsing function.
                   options: info, format, vep, filter or pref.

        Column 3 - Optional. Alternative name for column header.

        To make a config file with all available options from a VCF, run:
            vcf_parse -l path_to_input_vcf > config.txt
        \n'''
    ))


    # OPTIONAL: Lists all headers in a vcf then exits
    parser.add_argument(
        '-l', '--config_list', action='store_true', 
        help=textwrap.dedent(
        '''
        Return a list of all availabile config to the screen, then exit.
        See CONFIG section for usage.
        \n'''
    ))


    # OPTIONAL: Filter out any variants where FILTER column is not PASS
    parser.add_argument(
        '-F', '--filter_non_pass', action='store_true', 
        help=textwrap.dedent(
        '''
        Filters out any variants where the FILTER annotation is not 
        PASS. If missing then there will be no fitering based on the
        FILTER annotation.
        \n'''
    ))

    return parser.parse_args()


# -- MAIN FUNCTION ----------------------------------------------------

def main(args):
    # setup logger
    logger = logging.getLogger('vcf_parse')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(levelname)s\t%(asctime)s\t%(name)s\t%(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info('running vcf_parse.py...')

    # Load arguments, make vcf report object and load data
    report = vcf_report()
    report.load_data(args.input, args.output)

    # If -l flag called, print headers and exit
    if args.config_list:
        report.list_config()
        exit()

    # If config file provided, load config
    if args.config:
        report.load_config(args.config)
    else:
        logger.info('no config file found -- outputting all data from VCF.')

    # Make variant report of whole VCF
    report.make_report(args.filter_non_pass)

    # If preferred transcripts provided, apply to variant report
    if args.transcripts:
        pt = preferred_transcripts()
        pt.load(args.transcripts)
        pt.apply(report, args.transcript_strictness)
    else:
        logger.info('no preferred transcripts file provided -- preferred ' +
        'transcripts column will all be labelled as "Unknown"')

    # If known variants provided, apply to variant report
    if args.known_variants:
        known = known_variants()
        known.load_known_variants(args.known_variants)
        known.apply_known_variants(report)
    
    else:
        logger.info('no known variants file provided -- Classification ' +
        'column will be empty')

    # If single BED file provided, make variant report with BED file 
    # applied
    if args.bed:
        bed = bed_object()
        bed.apply_single(args.bed, report)

    # If folder of BED file provided, make a seperate variant report 
    # for each BED file. Output will be saved in a folder named the 
    # same as the BED file folder, within the output directory.
    elif args.bed_folder:
        bed = bed_object()
        bed.apply_multiple(args.bed_folder, report)

    # If no BED files provided, pass
    else:
        logger.info('no BED files provided')

    # Finish
    logger.info('vcf_parse.py completed\n{}'.format('---'*30))


# -- CALL FUNCTIONS ---------------------------------------------------

if __name__ == '__main__':
    args = get_args()
    main(args)
