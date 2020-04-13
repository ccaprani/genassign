# genassign
Generating assignments and solutions using LaTeX-PythonTex and jinja2 templates

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
and associated solution file are generated separtely and placed into
separate subfolders of the template file directory.

`genassign` is written to allow indpendent compilation of the template file
to facilitate development and checking of the questions and solutions,
including close control of the randomization.

It is not necessary for there to be PythonTex commands in the template.

## Useage
### Assignments
Prepare a template LaTeX-PytonTex file with complete questions and
solutions. Add the jinja templating variables to the document as necessary to
identify individualization (e.g. student name, ID, etc).
Include the LaTeX commands, and wrap the solutions as shown above.
Use PythonTex to randomize the problem variables upon each compilation.

*Standard example useage*:
```python
python genassign.py template.tex students.csv -t "Test 1 "
```
*To debug*:
```python
!debugfile('genassign.py', args='"template.tex" "students.csv"')
```

### Generic Useage
`genassign` can perform generic mail-merge functionality for LaTeX
documents. Use program option `-g` to enable generic mode. In this mode,
only one set of files is output to the `-r` root directory using:
    
* `-t` file mask

* `-f` folder mask

The masks are based on the columns numnber in the worksheet, and
constructed using `#d` as field variables for the column number, where
d is 1-9. An example is `'File_#2_#3'` in which the data in columns 2 and
3 (using 1-base numbdering) is subsituted for the file or folder name.

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
genassign.py [-h] [-t FILE_MASK] [-f FOLDER_MASK] [-b] [-g]
                [-s SOL_STEM] [-p PAPER_STEM] [-r ROOT] [-q QUESTDIR]
                template worksheet
```

optional arguments:

`-h`, `--help`
show this help message and exit

`-t`, `--file_mask` FILE_MASK
Test title filename prefix, or if in generic mode -g then the filename mask
                        
`-f`, `--folder_stem` FOLDER_MASK
Folder stem, for Moodle assignment types usually `onlinetext` or `file`
or if in generic mode -g then the subfolder name mask

`-b`, `--gen_paper`
Whether or not to hide solution and generate the paper

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

required named arguments:

`template`  LaTeX Template File with certain commands for jinja2
            and hiding solutions, e.g. `main.tex`
  
`worksheet` Student Moodle worksheet of specific format from
            assignment grading, e.g. `students.csv`
    
## Requirements
System requirements are working installations of Python, LaTeX, and
PythonTex. More specifically, `genassign` requires:
    
1. A LaTeX (optionally using PythonTex) template with certain specific
commands;

2. A Moodle grading worksheet (or generic database) for the assigment as
input.
        
## Template
There are two commands required at a minimum in the LaTeX file for Moodle
assignment output.

### Jinja2 Templating

The command for *jinja2* templating

```latex
    \newcommand*{\VAR}[1]{}
```

which has no effect on the template other than to identify variables
used for subsitution of student-specific information as defined in
Moodle worksheet:
    
* Student's full name: `\VAR{FullName}`

* Student's ID: `\VAR{StudentID}`

In case it is useful to have the fields to be replaced highlight ni the LaTeX
template, the templating command can be altered, e.g. to highlight the fields
in bold red:
    ```latex
    \newcommand*{\VAR}[1]{\textcolor{red}{\textbf{#1}}}
    ```
This formatting does not appear in the rendereed documents. If this is
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
operatin in generic mail-maerge mode.
    
## Documentation
To use `pdoc` to generate this documentation, issue this:
```
pdoc --html --force --output-dir . --config show_source_code=False genassign
```
