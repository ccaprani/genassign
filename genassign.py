# -*- coding: utf-8 -*-
r"""
*Generates Individualized Assignments and Solutions based on a LaTeX Template*

**Author:** Colin Caprani,
[colin.caprani@monash.edu](mailto://colin.caprani@monash.edu)

## Overview
`genassign` is a wrapper script that performs mail-merge like
functionality, with adaptations for generating assessments and solutions.
It does two main things:

1. It repeatedly calls a LaTeX-PythonTex template file and places
the output in subfolders of the template file directory.

2. It substitutes student-specific data into each generated file.

When the template file has randomization embedded, this is called
automatically at each compilation, resulting in individualized assignments.
Further, using a specific sequence of LaTeX commands, the question paper
and associated solution file are generated separately and placed into
separate subfolders of the template file directory.

`genassign` is written to allow independent compilation of the template file
to facilitate development and checking of the questions and solutions,
including close control of the randomization.

It is not necessary for there to be PythonTex commands in the template.

## Usage
### Assignments
Prepare a template LaTeX-PytonTex file with complete questions and
solutions. Add the jinja templating variables to the document as necessary to
identify individualization (e.g. student name, ID, etc).
Include the LaTeX commands, and wrap the solutions as shown above.
Use PythonTex to randomize the problem variables upon each compilation.

*Standard example usage*:
```python
python genassign.py -e template.tex students.csv -t "Test 1 "
```
*To debug*:
```python
!debugfile('genassign.py', args='-e "template.tex" "students.csv"')
```

### Generic Usage
`genassign` can perform generic mail-merge functionality for LaTeX
documents. Use program option `-g` to enable generic mode. In this mode,
only one set of files is output to the `-r` root directory using:
    
* `-t` file mask

* `-f` folder mask

The masks are based on the columns number in the worksheet, and
constructed using `#d` as field variables for the column number, where
d is 1-9. An example is `'File_#2_#3'` in which the data in columns 2 and
3 (using 1-base numbering) is substituted for the file or folder name.

An important restriction in this mode is that the column names, which are
the keys to be used in the LaTeX template, do not contain spaces, hyphens
or underscores.

Note that in the generic mode, it is not necessary for there to be the
`hidden` commands in the LaTeX document.

Example:
This will put the mail merge letters in the current folder with file names
id_name.pdf:
```python
python genassign.py letter.tex addresses.csv -g -t "#1_#2" -f . -r "letters"
```
    
## Commands
```
genassign.py [-h] [-t FILE_MASK] [-f FOLDER_MASK] [-b] [-g] [-e]
                [-s SOL_STEM] [-p PAPER_STEM] [-r ROOT] [-q QUESTDIR] 
                [-w PASSWORD]
                template worksheet
```

### Optional Arguments:

`-h`, `--help`
show this help message and exit

`-t`, `--file_mask` FILE_MASK
Test title filename prefix, or if in generic mode `-g` then the filename mask
                        
`-f`, `--folder_stem` FOLDER_MASK
Folder stem, for Moodle assignment types usually `onlinetext` or `file`
or if in generic mode `-g` then the subfolder name mask

`-b`, `--gen_paper`
If set, the paper without solutions will not be produced

`-e`, `--encrypt`
If set, the produced PDFs will be encrypted

`-g`, `--generic`
Operates in a generic mailmerge manner
                        
`-s`, `--sol_stem` SOL_STEM
Solutions filename stem, e.g. `'_sols'`
 
`-p`, `--paper_stem` PAPER_STEM
Question paper filename stem, e.g. `'_paper'`
 
`-r`, `--root` ROOT
Root directory name for main (solutions) output, e.g. `'solutions'`
 
`-q`, `--questdir` QUESTDIR
Directory name for questions output, e.g. `'questions'`

`-w`,`--password` PASSWORD
Password for encrypted PDFs, e.g. `'d0n0tC0py-21'`

### Required Named Arguments:

`template`  LaTeX Template File with certain commands for jinja2
            and hiding solutions, e.g. `main.tex`
  
`worksheet` Student Moodle worksheet of specific format from
            assignment grading, e.g. `students.csv`
    
## Requirements
System requirements are working installations of Python, LaTeX, and
PythonTex. More specifically, `genassign` requires:
    
1. A LaTeX (optionally using PythonTex) template with certain specific
commands;

2. A Moodle grading worksheet (or generic database) for the assignment as
input.

The Pandas library is also required, which can be obtained via PyPI or
Anaconda, depending on your python environment setup.
        
## Template
There are two commands required at a minimum in the LaTeX file for Moodle
assignment output.

### Jinja2 Templating

The command for *jinja2* templating

```latex
    \newcommand*{\VAR}[1]{}
```

which has no effect on the template other than to identify variables
used for substitution of student-specific information as defined in
Moodle worksheet:

* Student's full name: `\VAR{FullName}`

* Student's ID: `\VAR{StudentID}`

In case it is useful to have the fields to be replaced highlight ni the LaTeX
template, the templating command can be altered, e.g. to highlight the fields
in bold red:
    ```latex
    \newcommand*{\VAR}[1]{\textcolor{red}{\textbf{#1}}}
    ```
This formatting does not appear in the rendered documents. If this is
required, the `\VAR{Field}` should be wrapped in the desired formatting
in the document body.

### LaTeX Commands

The LaTeX commands to wrap the solutions, so they can be toggled on and
off must be placed in the document preamble. The following must appear:

```
\usepackage{comment}

\newif\ifhidden
% This defines whether to show the hidden content or not.
\hiddenfalse
\ifhidden 	% if \ hiddentrue
    \excludecomment{hidden}	% Exclude text within the "hidden" environment
\else   	% \ hiddenfalse
    \includecomment{hidden}	% Include text in the "hidden" environment
\fi
```

so that the solutions are wrapped in the document body as follows

```
\begin{hidden}
    ...LaTeX solution code, including PythonTex as necessary
\end{hidden}
```
Note that the LaTeX commands for hiding solutions are not required when
operating in generic mail-merge mode.
    
## Documentation
To use `pdoc` to generate this documentation, issue this:
```
pdoc --html --force --output-dir . --config show_source_code=False genassign
```
"""

import glob
import os
import stat
import shutil
import subprocess
import tempfile
import time
import fileinput
import argparse
import re
from types import SimpleNamespace
import jinja2  # https://tug.org/tug2019/slides/slides-ziegenhagen-python.pdf
import pandas as pd
import pikepdf


def make_template(texfile):
    """
    Creates the jinja2 template using a redefined template structure that
    plays nicely with LaTeX
    https://web.archive.org/web/20121024021221/http://e6h.de/post/11/

    Parameters
    ----------
    texfile : string
        The template LaTeX file containing jinja template variables.

    Returns
    -------
    jinja2 template
        jinja2 template used to render the documents.

    """
    path_lst = os.path.split(texfile)
    dir_path = path_lst[0]
    template_file = path_lst[1]
    
    latex_jinja_env = jinja2.Environment(
        block_start_string=r"\BLOCK{",  # instead of jinja's usual {%
        block_end_string=r"}",  # %}
        variable_start_string=r"\VAR{",  # {{
        variable_end_string=r"}",  # }}
        comment_start_string=r"\#{",  # {#
        comment_end_string=r"}",  # #}
        line_statement_prefix=r"%-",
        line_comment_prefix=r"%#",
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(os.path.abspath(dir_path))
        # loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__)))
    )

    # Load the template from a file
    return latex_jinja_env.get_template(template_file)


def render_file(values, keys, template, tmpfile):
    """
    Renders the tex file for compilation for a specific set of values

    Parameters
    ----------
    values : list of strings
        Contains the values to be placed against each template variable
    keys : list of strings
        Contains template variable names to be replaced
    template : jinja2 template
        sed to render the LaTeX file.
    tmpfile : string
        Name of the temporary files.

    Returns
    -------
    None.

    """

    # combine template and variables
    options = dict(zip(keys, values))
    document = template.render(**options)

    # write document
    with open(tmpfile + ".tex", "w") as outfile:
        outfile.write(document)


def remove_readonly(func, path, exc_info):
    """
    Attempts to remove a read-only file by changing the permissions.
    Note, all arguments are necessary, even if unused.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def compile_files(values, tmpfile, params):
    """
    Generates the Questions and Answers documents for a student

    Parameters
    ----------
    values : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    tmpfile : string
        Name of the temporary files.
    params : data structure
        Contains program parameters:
            * template = name of LaTeX template file
            * worksheet = name of data spreadsheet csv
            * file_mask = title of test typically, or masked filename
            * folder_mask = folder name stem as appropriate to the type of
                Moodle assigment - usually 'file' or 'onlinetext'.
                Or in generic mode the mask of the subfolder name.
            * gen_paper = whether or not to generate the test paper only.
            * generic = whether or not in generic "mailmerge" mode
            * sol_stem = filename postfix for solutions pdf
            * paper_stem = filename postfix for questions pdf
            * root = name of root (usually solutions) directory
            * questdir = name of questions directory

    Returns
    -------
    None.

    """

    # Compilation commands
    cmd_stem = " %s.tex" % tmpfile
    cmd_pdflatex = (
        "pdflatex -shell-escape -synctex=1 " + "-interaction=nonstopmode" + cmd_stem
    )
    cmd_pythontex = "pythontex " + cmd_stem

    # Ensure solutions are not hidden
    set_hidden(tmpfile + ".tex", hidden=False)

    # Compile full document including solutions
    # This step generates the variables & solutions
    subprocess.call(cmd_pdflatex, shell=True)
    subprocess.call(cmd_pythontex, shell=True)
    subprocess.call(cmd_pdflatex, shell=True)

    file_mask = params.file_mask
    folder_mask = params.folder_mask
    if not args.generic:
        file_mask += params.sol_stem

    move_pdf(
        tmpfile,
        params.root,
        demask(values, file_mask),
        demask(values, folder_mask),
        params.encrypt,
        params.password,
    )

    if params.gen_paper and not params.generic:
        # Compile test only, removing solutions
        set_hidden(tmpfile + ".tex", hidden=True)

        # Now compile LaTeX ONLY (to avoid generating any new random variables)
        # Do it twice to update toc
        subprocess.call(cmd_pdflatex, shell=True)
        subprocess.call(cmd_pdflatex, shell=True)

        # reset file mask
        file_mask = params.file_mask + params.paper_stem

        move_pdf(
            tmpfile,
            params.questdir,
            demask(values, file_mask),
            demask(values, folder_mask),
            params.encrypt,
            params.password,
        )


def move_pdf(tmpfile, root, file, folder, encrypt, password):
    """
    Moves the compiled PDF to the appropriate folder

    Parameters
    ----------
    tmpfile : string
        Name of the temporary files.
    root : string
        The name of the subfolder in which the student's folder will be placed.
        Usually one of 'solutions' or 'questions'
    file : string
        The filename to be used (no extension)
    folder : string
        The subfolder name to root folder where the file will be put
    encrypt : bool
        Whether or not to encrypt the PDF produced
    password : string
        The password to be used as the owner password if the file is encrypted

    Returns
    -------
    None.

    """
    try:
        # Rename & move the PDF file to a new subfolder
        file_pdf = file + ".pdf"
        if os.path.isfile(file_pdf):
            os.remove(file_pdf)
        os.rename(tmpfile + ".pdf", file_pdf)

        if encrypt:
            encrypt_pdf(file_pdf, password)

        # Create root if not exist
        if not os.path.exists(root):
            os.mkdir(root)

        # If folder exists delete it and contents
        file_path = os.path.join(root, folder)
        if os.path.exists(file_path):
            old = folder + "_" + tmpfile
            os.rename(folder, old)
            shutil.rmtree(old, onerror=remove_readonly)

        os.mkdir(file_path)
        shutil.move(file_pdf, os.path.join(file_path, file_pdf))
    except:
        print("*** ERROR: Cannot move rendered pdf: ", file_pdf)


def encrypt_pdf(file, password):
    """
    This function encrypts the PDF `file` using the provided password.

    Parameters
    ----------
    file : string
        The file to be encrypted using AES 256.
    password : string
        The owner password for the encryption (per PyMuPDF settings)

    Returns
    -------
    None.

    """
    # Set the appropriate permissions
    permissions = pikepdf.Permissions(
        accessibility=True,
        extract=False,
        modify_annotation=False,
        modify_assembly=False,
        modify_form=False,
        modify_other=False,
        print_lowres=True,
        print_highres=True,
    )

    # Get a temporary filename
    tmpfile = next(tempfile._get_candidate_names())
    tmpfile += ".pdf"

    # make a copy of the PDF
    shutil.copyfile(file, tmpfile)

    # Remove the original file
    os.remove(file)

    # Open the tempfile and save as the encrypted file
    pdf = pikepdf.Pdf.open(tmpfile)
    pdf.save(
        file,
        encryption=pikepdf.Encryption(owner=password, user="", R=6, allow=permissions),
    )

    # Now close and delete the tempfile
    pdf.close()
    os.remove(tmpfile)


def demask(values, mask):
    """
    Demasks a string masked with fields indicated by '#d' where d is a
    positive integer 1-9 using 1-based referencing of the entries in values.

    Parameters
    ----------
    values : list
        Values to be placed into mask string identified by 1-based index.
    mask : string
        Mask string including fields for substitution indicated by #d.

    Returns
    -------
    mask : string
        Demasked string with substituted values for the fields.

    """
    idx = [int(s) for s in re.findall(r"\#(\d)", mask)]
    for i in idx:
        mask = mask.replace("#" + str(i), str(values[i - 1]))
    return mask


def set_hidden(texfile, hidden=True):
    """
    Toggles the solutions visbility in the student's LaTeX file

    Parameters
    ----------
    texfile : string
        The template LaTeX file containing jinja template variables.
    hidden : bool, optional
        Whether or not the solutions are to be hidden. The default is True.

    Returns
    -------
    None.

    """
    # This relies on use of comment package with a new environment
    # called hidden defined which brackets solutions
    # A LaTeX primitive \ifhidden then turns this on or off

    hiddentrue = r"\hiddentrue"
    hiddenfalse = r"\hiddenfalse"

    str_find = hiddenfalse
    str_replace = hiddentrue
    if not hidden:
        str_find = hiddentrue
        str_replace = hiddenfalse

    with fileinput.FileInput(texfile, inplace=True, backup=".bak") as file:
        for line in file:
            print(line.replace(str_find, str_replace), end="")


def gen_files(values, keys, template, tmpfile, params):
    """
    Drives the rendering and compilation process for each student, and
    cleans up the files afterwards.

    Parameters
    ----------
    values : tuple of string
        Contains row of data: for student's: Moodle ID, Full Name, Student ID.
    keys : tuple of string
        Contains the field names of the data (i.e. worksheet column names)
    template : jinja2 template
        set to render the LaTeX file.
    tmpfile : string
        Name of the temporary files.
    params : data structure
        Contains program parameters:
            * template = name of LaTeX template file
            * worksheet = name of data spreadsheet csv
            * file_mask = title of test typically, or masked filename
            * folder_mask = folder name stem as appropriate to the type of
                Moodle assignment - usually 'file' or 'onlinetext'.
                Or in generic mode the mask of the subfolder name.
            * gen_paper = whether or not to generate the test paper only.
            * generic = whether or not in generic "mailmerge" mode
            * sol_stem = filename postfix for solutions pdf
            * paper_stem = filename postfix for questions pdf
            * root = name of root (usually solutions) directory
            * questdir = name of questons directory

    Returns
    -------
    None.

    """

    # Create student tex file
    render_file(values, keys, template, tmpfile)

    try:
        compile_files(values, tmpfile, params)

    finally:  # clean up files
        for f in glob.glob(tmpfile + ".*"):
            os.remove(f)
        path = "comment.cut"
        if os.path.exists(path):
            os.remove(path)
        path = "pythontex-files-" + tmpfile
        if os.path.exists(path):
            shutil.rmtree(path, onerror=remove_readonly)


def generic(csvfile):
    """
    Processes the csvfile to extract the dataframe and keys for use as a
    generic mail merge application.

    Parameters
    ----------
    csvfile : string
        The name of the worksheet containing the data.

    Returns
    -------
    df : dataframe
        The pandas dataframe object.
    keys : list of strings
        The keys for the data, i.e. the column names, which must be single
        words with no hyphens or underscores (must meet both python variable
        name rules and play nice with LaTeX)

    """
    df = pd.read_csv(csvfile)
    keys = list(df.columns.values)

    return df, keys


def moodle(csvfile):
    """
    Pre-processes usual inputs for the dataframe and more generic file
    and folder masks.

    Parameters
    ----------
    csvfile : string
        The name of the worksheet containing the student Moodle data.

    Returns
    -------
    df : dataframe
        The pandas dataframe object.
    keys : list of strings
        The keys for the Moodle data, i.e. adapted column names

    """
    # Parses a csv file from Moodle grading worksheet
    df = pd.read_csv(csvfile)
    df = df[["Identifier", "Full name", "ID number"]]
    df.Identifier = df.Identifier.str.replace("Participant ", "")
    df = df.rename(columns={"Identifier": "MoodleID", "ID number": "StudentID"})

    # List of keys to look for in template, suggest use CamelCase
    # - these are case sensitive
    # - and must be in same order as student-tuple
    # - canot use underscores, as these do not play nice in LaTeX
    # - cannot use hyphens, as these are not allowed in Python variables
    keys = ["MoodleID", "FullName", "StudentID"]

    return df, keys


def main(params):
    """
    The main function, called when file is run as script, allowing the other
    functions to be used from this script through a module interface

    Parameters
    ----------
    params : SimpleNameSpace collection of the argparse arguments
        The command line arguments parsed using argparse

    Returns
    -------
    None.

    """
    t = time.time()

    tmpfile = next(tempfile._get_candidate_names())
    template = make_template(params.template)

    # Clear output folders if they already exist
    if os.path.exists(params.root):
        shutil.rmtree(params.root, onerror=remove_readonly)
    if os.path.exists(params.questdir) and params.gen_paper:
        shutil.rmtree(params.questdir, onerror=remove_readonly)

    if not params.generic:
        df, keys = moodle(params.worksheet)
        params.file_mask = args.file_mask + "#2_#3"  # stems to be added later
        params.folder_mask = "#2_#1_assignsubmission_" + params.folder_mask + "_"
    else:
        params.gen_paper = False  # override generating paper
        df, keys = generic(params.worksheet)

    # Apply function to each row of df
    df.apply(
        gen_files, axis=1, keys=keys, template=template, tmpfile=tmpfile, params=params
    )

    print("")
    print("*** genassign has finished ***")
    if params.generic:
        print("Operating in generic mode")
    elif not params.gen_paper:
        print("* Warning: Paper generation was not requested")
    print(
        "Execution for %d individuals generated in %2.0f sec"
        % (len(df.index), time.time() - t)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render a LaTex Template \
                                     with variables defined from a Moodle \
                                         gradebook worksheet."
    )
    # Required args
    requiredargs = parser.add_argument_group("required named arguments")
    requiredargs.add_argument(
        "template",
        help="LaTeX Template File with certain commands\
                                  for jinja2 and hiding solutions",
    )
    requiredargs.add_argument(
        "worksheet",
        help="Student Moodle worksheet of \
                              specific format from assignment grading.",
    )
    # Main optionals
    parser.add_argument(
        "-t",
        "--file_mask",
        help="Test title filename prefix, or if in generic\
                        mode -g then the filename mask",
        required=False,
        default="",
    )
    parser.add_argument(
        "-f",
        "--folder_mask",
        help='Folder stem for Moodle assignment type\
                            usually "onlinetext" or "file"\
                            or if in generic mode -g then the foldername mask',
        required=False,
        default="file",
    )
    parser.add_argument(
        "-b",
        "--gen_paper",
        help="If set, the paper without solutions will not\
                        be produced",
        required=False,
        default=True,
        action="store_false",
    )
    parser.add_argument(
        "-e",
        "--encrypt",
        help="If set, the PDF files will be encrypted",
        required=False,
        default=False,
        action="store_true",
    )
    # Generic mode option
    parser.add_argument(
        "-g",
        "--generic",
        help="Operates in a generic mailmerge manner",
        required=False,
        default=False,
        action="store_true",
    )
    # Unusual optionals
    parser.add_argument(
        "-s",
        "--sol_stem",
        help="Solutions filename stem",
        required=False,
        default="_sols",
    )
    parser.add_argument(
        "-p",
        "--paper_stem",
        help="Question paper filename stem",
        required=False,
        default="_paper",
    )
    parser.add_argument(
        "-r",
        "--root",
        help="Root directory name for main (solutions) output",
        required=False,
        default="solutions",
    )
    parser.add_argument(
        "-q",
        "--questdir",
        help="Directory name for questions output",
        required=False,
        default="questions",
    )
    parser.add_argument(
        "-w",
        "--password",
        help="Password for encrypted PDFs",
        required=False,
        default="g3n@ss1gn-21",
    )
    args = parser.parse_args()

    # Strip any leading autocomplete from passed in filenames
    stripstr = r".\\"

    # Create a data structure of the args to pass around
    params = SimpleNamespace(
        template=args.template.lstrip(stripstr),
        worksheet=args.worksheet.lstrip(stripstr),
        file_mask=args.file_mask,
        folder_mask=args.folder_mask,
        gen_paper=args.gen_paper,
        encrypt=args.encrypt,
        generic=args.generic,
        sol_stem=args.sol_stem,
        paper_stem=args.paper_stem,
        root=args.root,
        questdir=args.questdir,
        password=args.password,
    )

    main(params)
