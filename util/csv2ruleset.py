'''
Convert CSV file to a basic ruleset package
'''
import os
import pathlib
import re
import argparse
from numpy.core.numeric import full
import pandas as pd
from tqdm import tqdm

TPL_RULENAME_CM = 'cm_%s'
TPL_REGEXP_FILENAME = "resources_regexp_re%s.txt"
TPL_USED_RES_FILENAME = "used_resources.txt"
TPL_MATCHRULES_FILENAME = "resources_rules_matchrules.txt"
TPL_CONTEXTRULE_FILENAME = "contextRule_%s.txt"

SKIP_TERMS = set(['-', '_', ''])

# current path
FULLPATH = pathlib.Path(__file__).parent.absolute()

def __norm(s):
    '''
    Normalize the norm
    '''
    # remove the terms
    s2 = re.sub(r'[\\\/\-\s]', '_', s)
    # remove the multiple _
    s3 = re.sub(r'[_]{2,}', '_', s2)
    # make a upper
    s4 = s3.upper()

    return s4


def __norm_dense(s):
    '''
    Make a dense norm
    '''
    return re.sub(r'[_]', '', s)
    

def __term(s):
    '''
    Normalize the term
    '''
    s = str(s).strip().lower()
    return s


def mk_matchrule(norm):
    '''
    Make a matchrule line
    '''
    return """RULENAME="cm_{norm_dense}",REGEXP="\\b(?i)(?:%re{norm_dense})\\b",LOCATION="NA",NORM="{norm}"
""".format(norm=norm, norm_dense=__norm_dense(norm))


def create_file_used_resources(ruleset_name, text, output=FULLPATH):
    '''
    Create the file for all used files
    '''
    fn = TPL_USED_RES_FILENAME
    full_fn = os.path.join(
        output, ruleset_name, fn
    )
    with open(full_fn, 'w') as f:
        f.write(text)

    return os.path.join(
        '.', fn
    )


def create_file_matchrules(ruleset_name, text, output=FULLPATH):
    '''
    Create the file for the matchrules
    '''
    fn = TPL_MATCHRULES_FILENAME
    full_fn = os.path.join(
        output, ruleset_name, 'rules', fn
    )
    with open(full_fn, 'w') as f:
        f.write(text)

    return os.path.join(
        '.', 'rules', fn
    )


def create_file_regexp(ruleset_name, norm, text, output=FULLPATH):
    '''
    Creat the file for the resource regexp
    '''
    norm_dense = __norm_dense(norm)
    fn = TPL_REGEXP_FILENAME % norm_dense
    full_fn = os.path.join( output, ruleset_name, 'regexp', fn )
    with open(full_fn, 'w') as f:
        f.write(text)
    
    return os.path.join(
        '.', 'regexp', fn
    )


def convert_to_ruleset(full_fn, output=FULLPATH, tmode='one', add_norm='yes'):
    '''
    Convert the file to ruleset format
    '''
    if full_fn.endswith('.csv'):
        df = pd.read_csv(full_fn)

    elif full_fn.endswith('.tsv'):
        df = pd.read_csv(full_fn, sep="\t")

    elif full_fn.endswith('.xlsx') or full_fn.endswith('.xls'):
        df = pd.read_excel(full_fn)

    else:
        raise Exception('Not support file format')

    # get the file name as the ruleset name for creating folder
    ruleset_name = pathlib.Path(full_fn).stem

    # the first column is the norm
    col_norm = df.columns[0]
    # the second column is the text or term
    col_term = df.columns[1]

    # create a dictionary for the output
    r_dict = {}

    # loop on each record
    for idx, row in tqdm(df.iterrows()):
        norm = row[col_norm]
        term = row[col_term]

        # make sure the term is a text
        term = str(term)

        # get the normalized norm and text
        norm_normed = __norm(norm)

        # use the normalized norm to make sure no duplicated
        if norm_normed not in r_dict:
            if add_norm == 'yes':
                r_dict[norm_normed] = {
                    "dict": set([norm_normed]),
                    "items": [norm_normed]
                }
            else:
                r_dict[norm_normed] = {
                    "dict": set([]),
                    "items": []
                }

        if tmode == 'more':
            term_list = term.split(';')
            for _term in term_list:
                term_normed = __term(term)

                # skip those useless terms
                if term_normed in SKIP_TERMS: continue

                # add the normed terms
                if term_normed not in r_dict[norm_normed]["dict"]:
                    # ok, a new term
                    r_dict[norm_normed]["dict"].add(term_normed)
                    # add the original term to list
                    r_dict[norm_normed]["items"].append(_term)

        else:
            # usually just one term
            term_normed = __term(term)

            # skip those useless terms
            if term_normed in SKIP_TERMS: continue

            # add the normed terms
            if term_normed not in r_dict[norm_normed]["dict"]:
                # ok, a new term
                r_dict[norm_normed]["dict"].add(term_normed)
                # add the original term to list
                r_dict[norm_normed]["items"].append(term)
        
    print('* found %s norms' % (
        len(r_dict)
    ))

    # now begin to save the files
    # first, mkdir
    # before saving, make sure the foler exsits

    folders = [
        os.path.join( output, ruleset_name ),
        os.path.join( output, ruleset_name, 'rules' ),
        os.path.join( output, ruleset_name, 'regexp' ),
        os.path.join( output, ruleset_name, 'context' ),
    ]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print('* created %s' % folder)
        else:
            print('* found %s' % folder)

    # then create the files according to norm and text
    matchrules = []
    used_resources = []
    for norm in tqdm(r_dict):
        items = r_dict[norm]["items"]
        text = '\n'.join(items)

        # save the rules
        matchrule = mk_matchrule(norm)
        matchrules.append(matchrule)

        # save the regexp file
        fn = create_file_regexp(ruleset_name, norm, text, output)

        # add this file to used resources
        used_resources.append(fn)

    # save the matchrules
    fn = create_file_matchrules(
        ruleset_name, '\n'.join(matchrules), output
    )
    used_resources.append(fn)

    # save the used_resources
    used_resources.append(os.path.join(
        '.', TPL_USED_RES_FILENAME
    ))
    create_file_used_resources(
        ruleset_name, '\n'.join(used_resources), output
    )

    print('* done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converter for Building MedTagger Ruleset')

    # add paramters
    parser.add_argument("fn", type=str,
        help="The path to the data file (csv, tsv, xls, or xlsx)")
    parser.add_argument("--tmode", type=str, default='one',
        choices=['one', 'more'],
        help="The term mode in the second column, one term or more?")
    parser.add_argument("--add_norm", type=str, default='yes',
        choices=['yes', 'no'], help="add norm itself to list?")
    parser.add_argument("--out", type=str,
        help="The output folder")

    # parse
    args = parser.parse_args()
    convert_to_ruleset(args.fn, args.out, args.tmode, args.add_norm)
