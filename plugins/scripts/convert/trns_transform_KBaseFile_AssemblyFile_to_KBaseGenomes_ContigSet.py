#!/usr/bin/env python

# standard library imports
from __future__ import print_function
import os
import sys
import logging
import re
import hashlib

# KBase imports
import biokbase.Transform.script_utils as script_utils
from biokbase.workspace.client import Workspace
import requests
import json

__VERSION__ = '0.0.1'

# on the prod ws, this is 3.0
CS_MD5_TYPE = 'KBaseGenomes.ContigSet-db7f518c9469d166a783d813c15d64e9'

SCRIPT_NAME = 'trns_transform_KBaseFile_AssemblyFile_to_KBaseGenomes_ContigSet'

TOKEN = os.environ.get('KB_AUTH_TOKEN')

# TODO simplify code - remove fasta-key, found_sequence

# TODO this is almost entirely duplicated in Jason's fasta->CS script. Move?
# copied from Jason's fasta-CS script. Some unnecessary parts were cut out,
# but the core code is the same.

# conversion method that can be called if this module is imported
# Note the logger has different levels it could be run.
#  See: https://docs.python.org/2/library/logging.html#logging-levels
# The default level is set to INFO which includes everything except DEBUG
def convert_to_contigs(shock_service_url, handle_service_url, input_file_name,
                       contigset_id, working_directory, shock_id,
                       handle_id, fasta_reference_only, source,
                       level=logging.INFO, logger=None):
    """
    Converts KBaseFile.AssemblyFile to KBaseGenomes.ContigSet and saves to WS.
    Note the MD5 for the contig is generated by uppercasing the sequence.
    The ContigSet MD5 is generated by taking the MD5 of joining the sorted list
    of individual contig's MD5s with a comma separator

    Args:
        shock_service_url: A url for the KBase SHOCK service.
        handle_service_url: A url for the KBase Handle Service.
        input_file_name: A file name for the input FASTA data.
        contigset_id: The id of the ContigSet. If not
            specified the name will default to the name of the input file
            appended with "_contig_set"'
        working_directory: The directory the resulting json file will be
            written to.
        shock_id: Shock id for the fasta file if it already exists in shock
        handle_id: Handle id for the fasta file if it already exists as a
            handle
        fasta_reference_only: Creates a reference to the fasta file in Shock,
            but does not store the sequences in the workspace object.
            Not recommended unless the fasta file is larger than 1GB.
            This is the default behavior for files that large.
        level: Logging level, defaults to logging.INFO.
    """

    if logger is None:
        logger = script_utils.stderrlogger(__file__)

    logger.info("Starting conversion of FASTA to KBaseGenomes.ContigSet")

    logger.info("Building Object.")

    if not os.path.isfile(input_file_name):
        raise Exception("The input file name {0} is not a file!".format(
            input_file_name))

    # default if not too large
    contig_set_has_sequences = True
    if fasta_reference_only:
        contig_set_has_sequences = False

    fasta_filesize = os.stat(input_file_name).st_size
    if fasta_filesize > 1000000000:
        # Fasta file too large to save sequences into the ContigSet object.
        contigset_warn = 'The FASTA input file seems to be too large. A ' +\
            'ContigSet object will be created without sequences, but will ' +\
            'contain a reference to the file.'
        logger.warning(contigset_warn)
        contig_set_has_sequences = False

    input_file_handle = open(input_file_name, 'r')
    fasta_header = None
    sequence_list = []
    fasta_dict = dict()
    first_header_found = False
    contig_set_md5_list = []
    # Pattern for replacing white space
    pattern = re.compile(r'\s+')
    sequence_exists = False
    for current_line in input_file_handle:
        if (current_line[0] == ">"):
            # found a header line
            # Wrap up previous fasta sequence
            if (not sequence_exists) and first_header_found:
                raise Exception(
                    "There is no sequence related to FASTA record: {0}".format(
                        fasta_header))
            if not first_header_found:
                first_header_found = True
            else:
                # build up sequence and remove all white space
                total_sequence = ''.join(sequence_list)
                total_sequence = re.sub(pattern, '', total_sequence)
                fasta_key = fasta_header.strip()
                if not total_sequence:
                    raise Exception(
                        "There is no sequence related to FASTA record: " +
                        fasta_key)
                contig_dict = dict()
                contig_dict["id"] = fasta_key
                contig_dict["length"] = len(total_sequence)
                contig_dict["name"] = fasta_key
                contig_dict["description"] = "Note MD5 is generated from " +\
                    "uppercasing the sequence"
                contig_md5 = hashlib.md5(total_sequence.upper()).hexdigest()
                contig_dict["md5"] = contig_md5
                contig_set_md5_list.append(contig_md5)
                if contig_set_has_sequences:
                    contig_dict["sequence"] = total_sequence
                else:
                    contig_dict["sequence"] = ""
                fasta_dict[fasta_key] = contig_dict

                # get set up for next fasta sequence
                sequence_list = []
                sequence_exists = False
            fasta_header = current_line.replace('>', '')
        else:
            sequence_list.append(current_line)
            sequence_exists = True

    input_file_handle.close()

    # wrap up last fasta sequence
    if (not sequence_exists) and first_header_found:
        raise Exception(
            "There is no sequence related to FASTA record: {0}".format(
                fasta_header))
    elif not first_header_found:
        raise Exception("There are no contigs in this file")
    else:
        # build up sequence and remove all white space
        total_sequence = ''.join(sequence_list)
        total_sequence = re.sub(pattern, '', total_sequence)
        fasta_key = fasta_header.strip()
        if not total_sequence:
            raise Exception(
                "There is no sequence related to FASTA record: " + fasta_key)
        contig_dict = dict()
        contig_dict["id"] = fasta_key
        contig_dict["length"] = len(total_sequence)
        contig_dict["name"] = fasta_key
        contig_dict["description"] = "Note MD5 is generated from " +\
            "uppercasing the sequence"
        contig_md5 = hashlib.md5(total_sequence.upper()).hexdigest()
        contig_dict["md5"] = contig_md5
        contig_set_md5_list.append(contig_md5)
        if contig_set_has_sequences:
            contig_dict["sequence"] = total_sequence
        else:
            contig_dict["sequence"] = ""
        fasta_dict[fasta_key] = contig_dict

    contig_set_dict = dict()
    contig_set_dict["md5"] = hashlib.md5(",".join(sorted(
        contig_set_md5_list))).hexdigest()
    contig_set_dict["id"] = contigset_id
    contig_set_dict["name"] = contigset_id
    s = 'unknown'
    if source and source['source']:
        s = source['source']
    contig_set_dict["source"] = s
    sid = os.path.basename(input_file_name)
    if source and source['source_id']:
        sid = source['source_id']
    contig_set_dict["source_id"] = sid
    contig_set_dict["contigs"] = [fasta_dict[x] for x in sorted(
        fasta_dict.keys())]

    contig_set_dict["fasta_ref"] = shock_id

    logger.info("Conversion completed.")
    return contig_set_dict


def download_workspace_data(ws_url, source_ws, source_obj, working_dir,
                            logger):
    ws = Workspace(ws_url, token=TOKEN)
    objdata = ws.get_objects([{'ref': source_ws + '/' + source_obj}])[0]
    info = objdata['info']
    if info[2].split('-')[0] != 'KBaseFile.AssemblyFile':
        raise ValueError(
            'This method only works on the KBaseFile.AssemblyFile type')
    shock_url = objdata['data']['assembly_file']['file']['url']
    shock_id = objdata['data']['assembly_file']['file']['id']
    ref = str(info[6]) + '/' + str(info[0]) + '/' + str(info[4])
    source = objdata['data'].get('source')

    outfile = os.path.join(working_dir, source_obj)
    shock_node = shock_url + '/node/' + shock_id + '/?download'
    headers = {'Authorization': 'OAuth ' + TOKEN}
    with open(outfile, 'w') as f:
        response = requests.get(shock_node, stream=True, headers=headers)
        if not response.ok:
            try:
                err = json.loads(response.content)['error'][0]
            except:
                logger.error("Couldn't parse response error content: " +
                             response.content)
                response.raise_for_status()
            raise Exception(str(err))
        for block in response.iter_content(1024):
            if not block:
                break
            f.write(block)

    return shock_url, shock_id, ref, source


def upload_workspace_data(cs, ws_url, source_ref, target_ws, obj_name):
    ws = Workspace(ws_url, token=TOKEN)
    type_ = ws.translate_from_MD5_types([CS_MD5_TYPE])[CS_MD5_TYPE][0]
    ws.save_objects(
        {'workspace': target_ws,
         'objects': [{'name': obj_name,
                      'type': type_,
                      'data': cs,
                      'provenance': [{'script': SCRIPT_NAME,
                                      'script_ver': __VERSION__,
                                      'input_ws_objects': [source_ref],
                                      }]
                      }
                     ]
         }
    )


def main():
    parser = script_utils.ArgumentParser(
        prog=SCRIPT_NAME,
        description='Converts KBaseFile.AssemblyFile to  ' +
        'KBaseGenomes.ContigSet.',
        epilog='Authors: Jason Baumohl, Matt Henderson, Gavin Price')
    # The following 7 arguments should be standard to all uploaders
    parser.add_argument(
        '--working_directory',
        help='Directory for temporary files',
        action='store', type=str, required=True)

    # Example of a custom argument specific to this uploader
    parser.add_argument('--workspace_service_url',
                        help='workspace service url',
                        action='store', type=str, required=True)
    parser.add_argument(
        '--source_workspace_name', help='name of the source workspace',
        action='store', type=str, required=True)
    parser.add_argument(
        '--destination_workspace_name', help='name of the target workspace',
        action='store', type=str, required=True)
    parser.add_argument(
        '--source_object_name',
        help='name of the workspace object to convert',
        action='store', type=str, required=True)
    parser.add_argument(
        '--destination_object_name',
        help='name for the produced ContigSet.',
        action='store', type=str, required=True)

    parser.add_argument(
        '--fasta_reference_only',
        help='Creates a reference to the fasta file in Shock, but does not ' +
        'store the sequences in the workspace object.  Not recommended ' +
        'unless the fasta file is larger than 1GB. This is the default ' +
        'behavior for files that large.', action='store_true', required=False)

    # ignore unknown arguments for now
    args, _ = parser.parse_known_args()

    logger = script_utils.stderrlogger(__file__)
    try:
        # make there's at least something for a token
        if not TOKEN:
            raise Exception("Unable to retrieve KBase Authentication token!")

        shock_url, shock_id, ref, source = download_workspace_data(
            args.workspace_service_url,
            args.source_workspace_name,
            args.source_object_name,
            args.working_directory,
            logger)

        inputfile = os.path.join(args.working_directory,
                                 args.source_object_name)

        cs = convert_to_contigs(
            None, None, inputfile,
            args.destination_object_name, args.working_directory,
            shock_id, None, args.fasta_reference_only, source, logger=logger)

        upload_workspace_data(
            cs, args.workspace_service_url, ref,
            args.destination_workspace_name, args.destination_object_name)
    except Exception, e:
        logger.exception(e)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
