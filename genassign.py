# -*- coding: utf-8 -*-
r"""
*Generates Individualized Assignments and Solutions based on a LaTeX Template*

**Author:** Colin Caprani,
[colin.caprani@monash.edu](mailto://colin.caprani@monash.edu)

Overview:
    `genassign` is a wrapper script that does two main things:
    
    1. It repeatedly calls a LaTeX-PythonTex template file and places
    the output in subfolders of the template file directory.
    
    2. It substitutes student-specific data into each generated file.
    
    When the template file has randomization embedded, this is called
    automatically at each compilation, resulting in individualized assignments.
    Further, using a specific sequence of LaTeX commands, the question paper
    and associated solution file are generated separtely and placed into
    separate subfolders of the template file directory.
    
    `genassign` is written to allow indpendent compilation of the template file
    to facilitate deveopment and checking of the questions and solutions,
    including close control of the randomization.
    
    It is not necessary for there to be PythonTex commands in the template.
    
Useage:
    Prepare a template LaTeX-PytonTex file with complete questions and
    solutions. Add the jinja templating variables to the document as necessary.
    Include the LaTeX commands, and wrap the solutions as shown above.
    Use PythonTex to randomize the problem variables upon each compilation.
    
    Standard example useage:
    ```python
    python genassign.py main.tex students.csv -t "Test 1"
    ```
    To debug:
    ```python
    !debugfile('genassign.py', args='"main.tex" "students.csv"')
    ```
    
Commands:
    ```
    genassign.py [-h] [-t TITLE] [-m MOODLE_STEM] [-s SOL_STEM]
                    [-p PAPER_STEM] [-a ANSDIR] [-q QUESTDIR]
                    template worksheet
    ```
    
    optional arguments:
    
    `-h`, `--help`
    show this help message and exit
    
    `-t`, `--title`
    Test title filename prefix
                            
    `-m`, `--moodle_stem`
    Moodle assignment type folder stem, usually `onlinetext` or `file`
                            
    `-s`, `--sol_stem`
    Solutions filename stem, e.g. `'_sols'`
     
    `-p`, `--paper_stem`
    Question paper filename stem, e.g. `'_paper'`
     
    `-a`, `--ansdir`
    Directory name for solutions output, e.g. `'solutions'`
     
    `-q`, `--questdir`
    Directory name for questions output, e.g. `'questions'`
    
    required named arguments:
    
    `template`  LaTeX Template File with certain commands for jinja2
                and hiding solutions, e.g. `main.tex`
      
    `worksheet` Student Moodle worksheet of specific format from
                assignment grading, e.g. `students.csv`
    
Requirements:
    System requirements are working installations of Python, LaTeX, and
    PythonTex. More specifically, `genassign` requires:
        
    1. A LaTeX-PythonTex template with certain specific commands
    
    2. A Moodle grading worksheet for the assigment as input
        
Template:
    There are two commands required at a minimum in the LaTeX file.
    
    *Jinja2 Templating*
    
    The command for *jinja2* templating
    
    ```
        \newcommand*{\VAR}[1]{}
    ```
    
    which has no effect on the template other than to identify variables
    used for subsitution of student-specific information as defined in
    Moodle worksheet:
        
    * Student's full name: `\VAR{FULL_NAME}`
    
    * Student's ID: `\VAR{STUDENT_ID}`
    
    *LaTeX Commands*
    
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
    
Documentation:
    To use `pdoc` to generate this documentation, issue this:
    ```
    pdoc --html --force --config show_source_code=False genassign
    ```
    And to generate a PDF of the documentation, first generate the markdown
    to the standard output stream and pipe it to `doc.text`:
    ```
    pdoc --pdf --force --config show_source_code=False genassign > doc.txt
    ```
    then issue this command:
    ```
    pandoc --metadata=title:"genassign Documentation" --toc --toc-depth=4 --from=markdown+abbreviations --pdf-engine=xelatex --output=genassign.pdf doc.txt
    ```
"""

import glob
import os
import stat
import shutil
import subprocess
import pandas as pd
import tempfile
import time
import jinja2  # https://tug.org/tug2019/slides/slides-ziegenhagen-python.pdf
import fileinput
import argparse


def make_template(texfile,tmpfile):
    """
    Creates the jinja2 template using a redefined template structure that
    plays nicely with LaTeX
    https://web.archive.org/web/20121024021221/http://e6h.de/post/11/

    Parameters
    ----------
    texfile : string
        The template LaTeX file containing jinja template variables.
    tmpfile : string
        The name of the temporary files that will be used.

    Returns
    -------
    jinja2 template
        jinja2 template used to render the documents.

    """
    latex_jinja_env = jinja2.Environment(
        block_start_string=r'\BLOCK{',      # instead of jinja's usual {%
        block_end_string=r'}',              # %}
        variable_start_string=r'\VAR{',     # {{
        variable_end_string=r'}',           # }}
        comment_start_string=r'\#{',        # {#
        comment_end_string=r'}',            # #}
        line_statement_prefix=r'%-',
        line_comment_prefix=r'%#',
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(os.path.abspath('.'))
        # loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__)))
    )
    
    # Load the template from a file
    return latex_jinja_env.get_template(texfile)
    
    
def render_student_tex_file(student,template,tmpfile):
    """
    Renders the tex file for compilation for a specific student

    Parameters
    ----------
    student : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    template : jinja2 template
        sed to render the LaTeX file.
    tmpfile : string
        Name of the temporary files.

    Returns
    -------
    None.

    """
    values = list(student)  # Converts student tuple to list
    # List of keys to look for in template
    # - these are case sensitive
    # - and must be in same order as student-tuple
    keys = ['MOODLE_ID','FULL_NAME','STUDENT_ID']
    
    # combine template and variables
    options = dict(zip(keys, values))
    document = template.render(**options)
    
    # write document
    with open(tmpfile+'.tex','w') as outfile:
        outfile.write(document)


def student_strings(student,moodle_str):
    """
    Creates the file and folder name strings for a student

    Parameters
    ----------
    student : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    moodle_str : string
        Folder name stem as appropriate to the type of Moodle assigment.
        Usually 'file' or 'onlinetext'

    Returns
    -------
    student_file : string
        The student-specific part of the pdf filename
    student_folder : string
        The student-specific part of the folder name

    """
    moodle_id, full_name, student_id = student
    student_file = '%s_%s' % (full_name,student_id)
    student_folder = '%s_%s_assignsubmission_%s_' \
        % (full_name,moodle_id,moodle_str)
    return student_file,student_folder


def remove_readonly(func, path, excinfo):
    """Attempts to remove a read-only file by changing the permissions"""
    os.chmod(path, stat.S_IWRITE)
    func(path)
    

def gen_q_and_a(student,assign_strings):
    """
    Generates the Questions and Answers documents for a student

    Parameters
    ----------
    student : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    assign_strings : tuple of strings
        Contains prgram string variables in the order:
            tmpfile = temporary file name
            moodle_str = older name stem as appropriate to the type of
                Moodle assigment. Usually 'file' or 'onlinetext'
            filename_prefix = title of test typically
            solutions_stem = filename postfix for solutions pdf
            questions_stem = filename postfix for questions pdf
            solutions_dir = name of solutions directory
            questions_dir = name of questons directory

    Returns
    -------
    None.

    """
    # Unpack tuple
    (tmpfile,moodle_str,filename_prefix,
        solutions_stem,questions_stem,
        solutions_dir,questions_dir) = assign_strings
    
    # Compilation commands
    cmd_stem = " %s.tex" % tmpfile
    cmd_pdflatex = 'pdflatex -shell-escape -synctex=1 ' \
        + '-interaction=nonstopmode' + cmd_stem
    cmd_pythontex = 'pythontex ' + cmd_stem
    
    # Ensure solutions are not hidden
    set_hidden(tmpfile+'.tex',hidden=False)
    
    # Compile full document including solutions
    # This step generates the variables & solutions
    subprocess.call(cmd_pdflatex, shell=True)
    subprocess.call(cmd_pythontex, shell=True)
    subprocess.call(cmd_pdflatex, shell=True)
    
    move_pdf(student,tmpfile,solutions_dir,
             solutions_stem,moodle_str,filename_prefix)
    
    # Compile test only, removing solutions
    set_hidden(tmpfile+'.tex',hidden=True)
    
    # Now compile LaTeX ONLY (to avoid generating any new random variables)
    # Do it twice to update toc
    subprocess.call(cmd_pdflatex, shell=True)
    subprocess.call(cmd_pdflatex, shell=True)
    
    move_pdf(student,tmpfile,questions_dir,
             questions_stem,moodle_str,filename_prefix)
    
    
def move_pdf(student,tmpfile,root,file_stem,moodle_str,prefix):
    """
    Moves the compiled PDF to the appropriate folder

    Parameters
    ----------
    student : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    tmpfile : string
        Name of the temporary files.
    root : string
        The name of the subfodler in which the student's folder will be placed.
        Usually one of 'solutions' or 'questions'
    file_stem : string
        Postfix to be applied to student-specific string to distinguish
        questions from solutions
    moodle_str : string
        Folder name stem as appropriate to the type of Moodle assigment.
        Usually 'file' or 'onlinetext'
    prefix : string
        Prefix to be applied to the student-specific filenames. Usually the
        title of the test.

    Returns
    -------
    None.

    """
    try:
        # Rename & move the PDF file to a new subfolder
        student_file,student_folder = student_strings(student,moodle_str)
        student_pdf = prefix + student_file + file_stem + '.pdf'
        if os.path.isfile(student_pdf):
            os.remove(student_pdf)
        os.rename(tmpfile+'.pdf', student_pdf)
        
        # Create root if not exist
        if not os.path.exists(root):
            os.mkdir(root)
        
        # If folder exists delete it and contents
        student_path = os.path.join(root, student_folder)
        if os.path.exists(student_path):
            old = student_folder + '_' + tempfile
            os.rename(student_folder,old)
            shutil.rmtree(old, onerror=remove_readonly)
    
        os.mkdir(student_path)
        shutil.move(student_pdf, os.path.join(student_path, student_pdf))
    except:
        print('*** ERROR: Cannot move student pdf: ', student_pdf)


def set_hidden(texfile,hidden=True):
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
    # A LaTeX primative \ifhidden then turns this on or off
    
    hiddentrue = r'\hiddentrue'
    hiddenfalse = r'\hiddenfalse'

    str_find = hiddenfalse
    str_replace = hiddentrue
    if not hidden:
        str_find = hiddentrue
        str_replace = hiddenfalse

    with fileinput.FileInput(texfile, inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace(str_find, str_replace), end='')

    
def gen_assign(student,template,assign_strings):
    """
    Drives the rendering and compilation process for each student, and
    cleans up the files afterwards.

    Parameters
    ----------
    student : tuple of string
        Contains student's data: Moodle ID, Full Name, Student ID.
    template : jinja2 template
        set to render the LaTeX file.
    assign_strings : tuple of strings
        Contains prgram string variables in the order:
            tmpfile = temporary file name
            moodle_str = older name stem as appropriate to the type of
                Moodle assigment. Usually 'file' or 'onlinetext'
            filename_prefix = title of test typically
            solutions_stem = filename postfix for solutions pdf
            questions_stem = filename postfix for questions pdf
            solutions_dir = name of solutions directory
            questions_dir = name of questons directory

    Returns
    -------
    None.

    """
    tmpfile = assign_strings[0]

    # Create student tex file
    render_student_tex_file(student,template,tmpfile)
    
    try:
        gen_q_and_a(student,assign_strings)
    
    finally:        # clean up files
        for f in glob.glob(tmpfile+".*"):
            os.remove(f)
        os.remove('comment.cut')
        shutil.rmtree('pythontex-files-' + tmpfile, onerror=remove_readonly)


def main(args):
    """
    The main function, called when file is run as script, allowing the other
    functions to be used from this script through a module interface

    Parameters
    ----------
    args : argparse arguments
        The command line arguments parsed using argparse

    Returns
    -------
    None.

    """
    t = time.time()
    
    # Main inputs
    texfile = args.template
    csvfile = args.worksheet
    # These will change each test
    moodle_str = args.moodle_stem
    filename_prefix = args.title
    # These are unlikely to change each test
    solutions_stem = args.sol_stem
    questions_stem = args.paper_stem
    solutions_dir = args.ansdir
    questions_dir = args.questdir
    
    # Parses a csv file from Moodle grading worksheet
    df = pd.read_csv(csvfile)
    df = df[["Identifier","Full name","ID number"]]
    df.Identifier = df.Identifier.str.replace('Participant ','')
    df = df.rename(columns={'Identifier': 'Moodle ID',
                            'ID number': 'Student ID'})
    
    tmpfile = next(tempfile._get_candidate_names())
    template = make_template(texfile,tmpfile)
    assign_strings = (tmpfile,moodle_str,filename_prefix,
                      solutions_stem,questions_stem,
                      solutions_dir,questions_dir)
    
    # Clear output folders if they already exist
    if os.path.exists(solutions_dir):
        shutil.rmtree(solutions_dir, onerror=remove_readonly)
    if os.path.exists(questions_dir):
        shutil.rmtree(questions_dir, onerror=remove_readonly)
       
    # Apply function to each row of df
    df.apply(gen_assign, axis=1, template=template,
             assign_strings=assign_strings)
    
    print('')
    print('*** genassign has finished ***')
    print("Papers & solutions for %d students generated in %2.0f sec"
          % (len(df.index), time.time() - t))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Render a LaTex Template \
                                     with variables defined from a Moodle \
                                         gradebook worksheet.')
    # Required args
    requiredargs = parser.add_argument_group('required named arguments')
    requiredargs.add_argument('template',
                              help='LaTeX Template File with certain commands\
                                  for jinja2 and hiding solutions')
    requiredargs.add_argument('worksheet',
                              help='Student Moodle worksheet of \
                              specific format from assignment grading.')
    # Main optionals
    parser.add_argument('-t','--title',
                        help='Test title filename prefix',
                        required=False, default='')
    parser.add_argument('-m','--moodle_stem',
                        help='Moodle assignment type \
                        folder stem', required=False, default='onlinetext')
    # Unusual optionals
    parser.add_argument('-s','--sol_stem',
                        help='Solutions filename stem',
                        required=False, default='_sols')
    parser.add_argument('-p','--paper_stem',
                        help='Question paper filename stem',
                        required=False, default='_paper')
    parser.add_argument('-a','--ansdir',
                        help='Directory name for solutions output',
                        required=False, default='solutions')
    parser.add_argument('-q','--questdir',
                        help='Directory name for questions output',
                        required=False, default='questions')
    args = parser.parse_args()
    
    main(args)
