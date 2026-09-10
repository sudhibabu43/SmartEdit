#!/usr/bin/python3
"""
 @file
 @brief Display all available string translations for each translation file
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author Frank Dana <ferdnyc AT gmail com>

 @section LICENSE

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with SmartEdit Library.  If not, see <http://www.gnu.org/licenses/>.
 """

import os
import re
import fnmatch
import sys

SRC_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from qt_api import QCoreApplication, QTranslator



language_path = os.path.dirname(os.path.abspath(__file__))


app = QCoreApplication(sys.argv)


all_templates = ['SmartEdit.pot', 'SmartEdit_transitions.pot', 'SmartEdit_blender.pot']
for template_name in all_templates:
    POT_source = open(os.path.join(language_path, 'SmartEdit', template_name)).read()
    all_strings = re.findall('^msgid \"(.*)\"', POT_source, re.MULTILINE)

    print("Scanning {} strings in all translation files...".format(len(all_strings)))

    
    for filename in fnmatch.filter(os.listdir(language_path), 'SmartEdit*.qm'):
        lang_code = filename[:-3]
        
        translator = QTranslator(app)

        
        if translator.load(lang_code, language_path):
            app.installTranslator(translator)

            print("\n=================================================")
            print("Showing translations for {}".format(filename))
            print("=================================================")
            
            for source_string in all_strings:
                translated_string = app.translate("", source_string)
                if source_string != translated_string:
                    print('  {} => {}'.format(source_string,translated_string))

                if "%s" in source_string or "%s(" in source_string or "%d" in source_string:
                    if source_string.count('%') != translated_string.count('%'):
                        raise(Exception('Invalid string replacement found: "%s" vs "%s" [%s]' %
                              (translated_string, source_string, lang_code)))

            
            app.removeTranslator(translator)
