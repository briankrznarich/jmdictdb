# Help formatters for Python's argparse module.
# Contents:
#   ParagraphFormatter (Stuart McGraw)
#   ParagraphFormatterML (Stuart McGraw)
#   FlexiFormatter (David Steele)

#=============================================================================
# See also: http://bugs.python.org/issue12806,
#  http://bugs.python.org/file22977/argparse_formatter.py

import argparse, re, textwrap
class ParagraphFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        return _para_reformat(self, text, width, multiline=False)
    def _fill_text(self, text, width, indent):
        lines =_para_reformat(self, text, width, indent, False)
        return '\n'.join(lines)

class ParagraphFormatterML(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        return _para_reformat(self, text, width, multiline=True)
    def _fill_text(self, text, width, indent):
        lines = _para_reformat(self, text, width, indent, True)
        return '\n'.join(lines)

def _para_reformat(self, text, width, indent='', multiline=False):
        new_lines = list()
        main_indent = len(re.match(r'( *)',text).group(1))
        def blocker (text):
            '''On each call yields 2-tuple consisting of a boolean
            and the next block of text from 'text'.  A block is
            either a single line, or a group of contiguous lines.
            The former is returned when not in multiline mode, the
            text in the line was indented beyond the indentation
            of the first line, or it was a blank line (the latter
            two jointly referred to as "no-wrap" lines).
            A block of concatenated text lines up to the next no-
            wrap line is returned when in multiline mode.  The
            boolean value indicates whether text wrapping should
            be done on the returned text.'''

            block = list()
            for line in text.splitlines():
                line_indent = len(re.match(r'( *)',line).group(1))
                isindented = line_indent - main_indent > 0
                isblank = re.match(r'\s*$', line)
                if isblank or isindented:       # A no-wrap line.
                    if block:
                          # Yield previously accumulated block
                          #  of text if any, for wrapping.
                        yield True, ''.join(block)
                        block = list()
                    yield False, line     # And now yield our no-wrap line.
                else:                     # We have a regular text line.
                    if multiline:         # In multiline mode accumulate it.
                        block.append(line)
                    else:                 # Not in multiline mode, yield it
                        yield True, line  #  for wrapping.
            if block:                     # Yield any text block left over.
                yield (True, ''.join(block))

        for wrap, line in blocker(text):
            if wrap:
                # We have either a single line or a group of concatented
                # lines.  Either way, we treat them as a block of text and
                # wrap them (after reducing multiple whitespace to just
                # single space characters).
                line = self._whitespace_matcher.sub(' ', line).strip()
                # Textwrap will do all the hard work for us.
                new_lines.extend(textwrap.wrap(text=line, width=width,
                                               initial_indent=indent,
                                               subsequent_indent=indent))
            else:
                # The line was a no-wrap one so leave the formatting alone.
                new_lines.append(line[main_indent:])

        return new_lines

#=============================================================================
# From https://pypi.org/project/argparse-formatter/
# 2020-01-20
# Mionor reformatting applied.
# See also ParagraphFormatter at the above URL,
#
# FlexiFormatter is
# Copyright (c) 2019 David Steele <dsteele@gmail.com>
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE

import argparse, re, textwrap
class FlexiFormatter(argparse.RawTextHelpFormatter):
    """FlexiFormatter which respects new line formatting and wraps the rest

    Example:
        >>> parser = argparse.ArgumentParser(formatter_class=FlexiFormatter)
        >>> parser.add_argument('--example', help='''\
        ...     This argument's help text will have this first long line\
        ...     wrapped to fit the target window size so that your text\
        ...     remains flexible.
        ...
        ...         1. This option list
        ...         2. is still persisted
        ...         3. and the option strings get wrapped like this with an\
        ...            indent for readability.
        ...
        ...     You must use backslashes at the end of lines to indicate that\
        ...     you want the text to wrap instead of preserving the newline.
        ...
        ...     As with docstrings, the leading space to the text block is\
        ...     ignored.
        ... ''')
        >>> parser.parse_args(['-h'])
        usage: argparse_formatter.py [-h] [--example EXAMPLE]

        optional arguments:
          -h, --help         show this help message and exit
          --example EXAMPLE  This argument's help text will have this first
                             long line wrapped to fit the target window size
                             so that your text remains flexible.

                                 1. This option list
                                 2. is still persisted
                                 3. and the option strings get wrapped like
                                    this with an indent for readability.

                             You must use backslashes at the end of lines to
                             indicate that you want the text to wrap instead
                             of preserving the newline.

                             As with docstrings, the leading space to the
                             text block is ignored.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return self._para_reformat(text, width)

    def _fill_text(self, text, width, indent):
        lines = self._para_reformat(text, width)
        return "\n".join(lines)

    def _para_reformat(self, text, width):
        text = textwrap.dedent(text).strip()
        lines = list()
        main_indent = len(re.match(r"( *)", text).group(1))
          # Wrap each line individually to allow for partial formatting
        for line in text.splitlines():
              # Get this line's indent and figure out what indent to use
              # if the line wraps. Account for lists of small variety.
            indent = len(re.match(r"( *)", line).group(1))
            list_match = re.match(r"( *)(([*-+>]+|\w+\)|\w+\.) +)", line)
            if list_match:
                sub_indent = indent + len(list_match.group(2))
            else:
                sub_indent = indent
              # Textwrap will do all the hard work for us
            line = self._whitespace_matcher.sub(" ", line).strip()
            new_lines = textwrap.wrap(
                text=line,
                width=width,
                initial_indent=" " * (indent - main_indent),
                subsequent_indent=" " * (sub_indent - main_indent), )
              # Blank lines get eaten by textwrap, put it back with [' ']
            lines.extend(new_lines or [" "])
        return lines
