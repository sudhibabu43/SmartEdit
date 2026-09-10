#!/usr/bin/python3
"""
 @file
 @brief This file updates the SmartEdit.POT (language translation template) by scanning all source files.
 @author Jonathan Thomas <jonathan@smartedit.org>

 This file helps you generate the POT file that contains all of the translatable
 strings / text in SmartEdit.  Because some of our text is in custom XML files,
 the xgettext command can't correctly generate the POT file.  Thus... the
 existence of this file. =)

 Command to create the individual language PO files (Ascii files)
		$ msginit --input=SmartEdit.pot --locale=fr_FR
		$ msginit --input=SmartEdit.pot --locale=es

 Command to update the PO files (if text is added or changed)
		$ msgmerge en_US.po SmartEdit.pot -U
		$ msgmerge es.po SmartEdit.pot -U

 Command to compile the Ascii PO files into binary MO files
		$ msgfmt en_US.po --output-file=en_US/LC_MESSAGES/SmartEdit.mo
		$ msgfmt es.po --output-file=es/LC_MESSAGES/SmartEdit.mo

 Command to compile all PO files in a folder
		$ find -iname "*.po" -exec msgfmt {} -o {}.mo \\;

 Command to combine the 2 pot files into 1 file
       $ msgcat ~/smartedit/locale/SmartEdit/SmartEdit_source.pot ~/smartedit/smartedit/locale/SmartEdit/SmartEdit_glade.pot -o ~/smartedit/main/locale/SmartEdit/SmartEdit.pot

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

import shutil
import datetime
import os
import subprocess
import sys
import re
import json


try:
  from defusedxml import minidom as xml
except ImportError:
  from xml.dom import minidom as xml

import smartedit


path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if path not in sys.path:
    sys.path.append(path)

import classes.info as info
from classes.logger import log
from classes.effect_init import effect_options


language_folder_path = os.path.dirname(os.path.abspath(__file__))
smartedit_path = os.path.dirname(language_folder_path)
effects_path = os.path.join(smartedit_path, 'effects')
blender_path = os.path.join(smartedit_path, 'blender')
transitions_path = os.path.join(smartedit_path, 'transitions')
titles_path = os.path.join(smartedit_path, 'titles')
export_path = os.path.join(smartedit_path, 'presets')
windows_ui_path = os.path.join(smartedit_path, 'windows', 'ui')

log.info("-----------------------------------------------------")
log.info(" Creating temp POT files")
log.info("-----------------------------------------------------")


temp_files = ['SmartEdit_source.pot', 'SmartEdit_glade.pot', 'SmartEdit_effects.pot', 'SmartEdit_export.pot',
              'SmartEdit_transitions.pot', 'SmartEdit_QtUi.pot']
for temp_file_name in temp_files:
    temp_file_path = os.path.join(language_folder_path, temp_file_name)
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    f = open(temp_file_path, "w")
    f.close()

log.info("-----------------------------------------------------")
log.info(" Using xgettext to generate .py POT files")
log.info("-----------------------------------------------------")


subprocess.call(r'find %s -iname "*.py" -exec xgettext -j -o %s --keyword=_ --keyword=N_ --keyword=_tr {} \;' % (
    smartedit_path, os.path.join(language_folder_path, 'SmartEdit_source.pot')), shell=True)

log.info("-----------------------------------------------------")
log.info(" Using Qt's lupdate to generate .ui POT files")
log.info("-----------------------------------------------------")


os.chdir(windows_ui_path)
subprocess.call('lupdate *.ui -ts %s' % (os.path.join(language_folder_path, 'SmartEdit_QtUi.ts')), shell=True)
subprocess.call('lupdate *.ui -ts %s' % (os.path.join(language_folder_path, 'SmartEdit_QtUi.pot')), shell=True)
os.chdir(language_folder_path)


output = open(os.path.join(language_folder_path, "clean.po"), 'w')
for line in open(os.path.join(language_folder_path, 'SmartEdit_QtUi.pot'), 'r'):
    if not line.startswith('msgctxt'):
        output.write(line)

output.close()
shutil.copy(os.path.join(language_folder_path, "clean.po"), os.path.join(language_folder_path, 'SmartEdit_QtUi.pot'))
os.remove(os.path.join(language_folder_path, "clean.po"))


subprocess.call('msguniq %s --use-first -o %s' % (os.path.join(language_folder_path, 'SmartEdit_QtUi.pot'),
                                                  os.path.join(language_folder_path, 'clean.po')), shell=True)
shutil.copy(os.path.join(language_folder_path, "clean.po"), os.path.join(language_folder_path, 'SmartEdit_QtUi.pot'))
os.remove(os.path.join(language_folder_path, "clean.po"))


log.info("-----------------------------------------------------")
log.info(" Updating auto created POT files to set CharSet")
log.info("-----------------------------------------------------")

temp_files = ['SmartEdit_source.pot', 'SmartEdit_glade.pot']
for temp_file in temp_files:
    
    f = open(os.path.join(language_folder_path, temp_file), "r")
    
    entire_source = f.read()
    f.close()

    
    entire_source = entire_source.replace("charset=CHARSET", "charset=UTF-8")

    
    if os.path.exists(os.path.join(language_folder_path, temp_file)):
        os.remove(os.path.join(language_folder_path, temp_file))
    f = open(os.path.join(language_folder_path, temp_file), "w")
    f.write(entire_source)
    f.close()

log.info("-----------------------------------------------------")
log.info(" Scanning effects & resources used by SmartEdit")
log.info("-----------------------------------------------------")

props = json.loads(smartedit.Clip().PropertiesJSON(1))


effects_text = {}
for key in props.keys():
    property = props[key]
    if "name" in property:
        effects_text[property["name"]] = "libsmartedit (Clip Properties)"
    if "choices" in property:
        for choice in property["choices"]:
            effects_text[choice["name"]] = "libsmartedit (Clip Properties)"


objects = json.loads(smartedit.EffectInfo.Json())
for object in objects:
    class_name = object.get("class_name")
    props = json.loads(smartedit.EffectInfo().CreateEffect(class_name).PropertiesJSON(1))

    
    for key in props.keys():
        property = props[key]
        if key == "objects":
            continue 
        if "name" in property:
            effects_text[property["name"]] = "libsmartedit (Effect Properties)"
        if "choices" in object:
            for choice in property["choices"]:
                effects_text[choice["name"]] = "libsmartedit (Effect Properties)"



for effect in effect_options:
    for param in effect_options[effect]:
        if "title" in param:
            effects_text[param["title"]] = "effect_init (Effect parameter for %s)" % effect
        if "values" in param:
            for value in param["values"]:
                effects_text[value["name"]] = "effect_init (Effect parameter for %s)" % effect


e = smartedit.EffectInfo()
props = json.loads(e.Json())


for effect in props:
    if "name" in effect:
        effects_text[effect["name"]] = "libsmartedit (Effect Metadata)"
    if "description" in effect:
        effects_text[effect["description"]] = "libsmartedit (Effect Metadata)"


for folder in os.listdir(info.COLORS_PATH):
    category_name = folder.replace("_", " ").title()
    folder_path = os.path.join(info.COLORS_PATH, folder)
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            basename, extension = os.path.splitext(filename)
            if filename.endswith(".cube"):
                lut_name = basename.replace("_", " ").title()
                effects_text[category_name] = "ColorMap effect lookup (Category)"
                effects_text[lut_name] = "ColorMap effect lookup (Name)"


emoji_text = { "translator-credits": "Translator credits to be translated by LaunchPad" }
emoji_metadata_path = os.path.join(info.PATH, "emojis", "data", "openmoji-optimized.json")
emoji_ignore_keys = ("Keyboard", "Sunset", "Key", "Right arrow", "Left arrow", "Bubbles",
                     "Twitter", "Instagram", "Scale", "Simple", "Close", "Forward", "Copy",
                     "Filter", "Details", "Duplicate", "Edit", "Delete")
with open(emoji_metadata_path, 'r', encoding="utf-8") as f:
    emoji_metadata = json.load(f)

    
    for filename, emoji in emoji_metadata.items():
        emoji_name = emoji["annotation"].capitalize()
        emoji_group = emoji["group"].split('-')[0].capitalize()
        if "annotation" in emoji and emoji_name not in emoji_ignore_keys:
            emoji_text[emoji_name] = "Emoji Metadata (Displayed Name)"
        if "group" in emoji and emoji_group not in effects_text and emoji_group not in emoji_ignore_keys:
            emoji_text[emoji_group] = "Emoji Metadata (Group Filter name)"


blender_text = { "translator-credits": "Translator credits to be translated by LaunchPad" }
blender_ignore_keys = ("Title", "Alpha", "Blur", "Font Name", "Yes", "No", "On", "Off", "Default")
for file in os.listdir(blender_path):
    if os.path.isfile(os.path.join(blender_path, file)):
        
        full_file_path = os.path.join(blender_path, file)
        xmldoc = xml.parse(os.path.join(blender_path, file))

        
        translation_key = xmldoc.getElementsByTagName("title")[0].childNodes[0].data
        if translation_key not in blender_ignore_keys:
            blender_text[translation_key] = full_file_path

        
        params = xmldoc.getElementsByTagName("param")

        
        for param in params:
            if param.attributes["title"]:
                translation_key = param.attributes["title"].value
                if translation_key not in blender_ignore_keys:
                    blender_text[param.attributes["title"].value] = full_file_path

                    
                    for child in param.childNodes:
                        if child.nodeName == "values":
                            for value in child.getElementsByTagName("value"):
                                if value.hasAttribute("name"):
                                    value_name = value.getAttribute("name")
                                    if value_name not in blender_ignore_keys:
                                        blender_text[value_name] = full_file_path


export_text = {}
for file in os.listdir(export_path):
    if os.path.isfile(os.path.join(export_path, file)):
        
        full_file_path = os.path.join(export_path, file)
        xmldoc = xml.parse(os.path.join(export_path, file))

        
        export_text[xmldoc.getElementsByTagName("type")[0].childNodes[0].data] = full_file_path
        export_text[xmldoc.getElementsByTagName("title")[0].childNodes[0].data] = full_file_path


settings_file = open(os.path.join(info.PATH, 'settings', '_default.settings'), 'r').read()
settings = json.loads(settings_file)
category_names = []
for setting in settings:
    if "type" in setting and setting["type"] != "hidden":
        
        export_text[setting["title"]] = "Settings for %s" % setting["setting"]
    if "type" in setting and setting["type"] != "hidden":
        
        if setting["category"] not in category_names:
            export_text[setting["category"]] = "Settings Category for %s" % setting["category"]
            category_names.append(setting["category"])
        if "translate_values" in setting and setting.get("translate_values"):
            
            for value in setting.get("values", []):
                export_text[value["name"]] = "Settings for %s" % setting["setting"]


from themes.manager import ThemeName
for theme_name in ThemeName.get_sorted_theme_names():
    export_text[theme_name] = "User-Interface Theme Name"


for manifest_name in ("yolo-models.json", "cutie-models.json", "efficient-sam-models.json"):
    manifest_path = os.path.join(info.RESOURCES_PATH, manifest_name)
    if not os.path.exists(manifest_path):
        continue
    with open(manifest_path, "r", encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    for model in manifest.get("models", []):
        if model.get("name"):
            export_text[model["name"]] = "AI model dropdown (%s name)" % manifest_name
        if model.get("description"):
            export_text[model["description"]] = "AI model dropdown (%s description)" % manifest_name


transitions_text = { "translator-credits": "Translator credits to be translated by LaunchPad" }
transitions_ignore_keys = ("Common", "Fade")
for file in os.listdir(transitions_path):
    
    full_file_path = os.path.join(transitions_path, file)
    (fileBaseName, fileExtension) = os.path.splitext(file)

    
    name = fileBaseName.replace("_", " ").capitalize()

    
    if name not in transitions_ignore_keys:
        transitions_text[name] = full_file_path

    
    for sub_file in os.listdir(full_file_path):
        
        full_subfile_path = os.path.join(full_file_path, sub_file)
        fileBaseName = os.path.splitext(sub_file)[0]

        
        suffix_number = None
        name_parts = fileBaseName.split("_")
        if name_parts[-1].isdigit():
            suffix_number = name_parts[-1]

        
        name = fileBaseName.replace("_", " ").capitalize()

        
        if suffix_number:
            name = name.replace(suffix_number, "%s")

        
        if name not in transitions_ignore_keys:
            transitions_text[name] = full_subfile_path


for sub_file in os.listdir(titles_path):
    
    full_subfile_path = os.path.join(titles_path, sub_file)
    fileBaseName = os.path.splitext(sub_file)[0]

    
    suffix_number = None
    name_parts = fileBaseName.split("_")
    if name_parts[-1].isdigit():
        suffix_number = name_parts[-1]

    
    name = fileBaseName.replace("_", " ").capitalize()

    
    if suffix_number:
        name = name.replace(suffix_number, "%s")

    
    transitions_text[name] = full_subfile_path


log.info("-----------------------------------------------------")
log.info(" Creating the custom XML POT files")
log.info("-----------------------------------------------------")


header_text = ""
header_text = header_text + '# SmartEdit Video Editor POT Template File.\n'
header_text = header_text + '# Copyright (C) 2008-2018 SmartEdit Studios, LLC\n'
header_text = header_text + '# This file is distributed under the same license as SmartEdit.\n'
header_text = header_text + '# Jonathan Thomas <Jonathan.Oomph@gmail.com>, 2018.\n'
header_text = header_text + '#\n'
header_text = header_text + '#, fuzzy\n'
header_text = header_text + 'msgid ""\n'
header_text = header_text + 'msgstr ""\n'
header_text = header_text + '"Project-Id-Version: SmartEdit Video Editor (version: %s)\\n"\n' % info.VERSION
header_text = header_text + '"Report-Msgid-Bugs-To: Jonathan Thomas <Jonathan.Oomph@gmail.com>\\n"\n'
header_text = header_text + '"POT-Creation-Date: %s\\n"\n' % datetime.datetime.now()
header_text = header_text + '"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n'
header_text = header_text + '"Last-Translator: Jonathan Thomas <Jonathan.Oomph@gmail.com>\\n"\n'
header_text = header_text + '"Language-Team: https://translations.launchpad.net/+groups/launchpad-translators\\n"\n'
header_text = header_text + '"MIME-Version: 1.0\\n"\n'
header_text = header_text + '"Content-Type: text/plain; charset=UTF-8\\n"\n'
header_text = header_text + '"Content-Transfer-Encoding: 8bit\\n"\n'


temp_files = [['SmartEdit_effects.pot', effects_text],
              ['SmartEdit_export.pot', export_text],
              ['SmartEdit_transitions.pot', transitions_text],
              ['SmartEdit_emojis.pot', emoji_text],
              ['SmartEdit_blender.pot', blender_text]
              ]
for temp_file, text_dict in temp_files:
    f = open(temp_file, "w")

    
    f.write(header_text)

    
    for k, v in text_dict.items():
        if k:
            f.write('\n')
            f.write('#: %s\n' % v)
            f.write('msgid "%s"\n' % k)
            f.write('msgstr ""\n')

    
    f.close()

log.info("-----------------------------------------------------")
log.info(" Combine all temp POT files using msgcat command ")
log.info(" (this removes dupes) ")
log.info("-----------------------------------------------------")

temp_files = ['SmartEdit_source.pot', 'SmartEdit_glade.pot', 'SmartEdit_effects.pot',
              'SmartEdit_export.pot', 'SmartEdit_QtUi.pot']
command = "msgcat"
for temp_file in temp_files:
    
    command = command + " " + os.path.join(language_folder_path, temp_file)
command = command + " -o " + os.path.join(language_folder_path, "SmartEdit", "SmartEdit.pot")

log.info(command)


subprocess.call(command, shell=True)

log.info("-----------------------------------------------------")
log.info(" Create FINAL POT File from all temp POT files ")
log.info("-----------------------------------------------------")


f = open(os.path.join(language_folder_path, "SmartEdit", "SmartEdit.pot"), "r")

entire_source = f.read()
f.close()


if os.path.exists(os.path.join(language_folder_path, "SmartEdit", "SmartEdit.pot")):
    os.remove(os.path.join(language_folder_path, "SmartEdit", "SmartEdit.pot"))
final = open(os.path.join(language_folder_path, "SmartEdit", "SmartEdit.pot"), "w")
final.write(header_text)
final.write("\n")


if os.path.exists(os.path.join(language_folder_path, "SmartEdit_transitions.pot")):
    os.rename(os.path.join(language_folder_path, "SmartEdit_transitions.pot"),
              os.path.join(language_folder_path, "SmartEdit", "SmartEdit_transitions.pot"))


if os.path.exists(os.path.join(language_folder_path, "SmartEdit_emojis.pot")):
    os.rename(os.path.join(language_folder_path, "SmartEdit_emojis.pot"),
              os.path.join(language_folder_path, "SmartEdit", "SmartEdit_emojis.pot"))


if os.path.exists(os.path.join(language_folder_path, "SmartEdit_blender.pot")):
    os.rename(os.path.join(language_folder_path, "SmartEdit_blender.pot"),
              os.path.join(language_folder_path, "SmartEdit", "SmartEdit_blender.pot"))


start_pos = entire_source.find("#: ")
trimmed_source = entire_source[start_pos:]


final.write(trimmed_source)
final.write("\n")


final.close()

log.info("-----------------------------------------------------")
log.info(" Remove all temp POT files ")
log.info("-----------------------------------------------------")


temp_files = ['SmartEdit_source.pot', 'SmartEdit_glade.pot', 'SmartEdit_effects.pot', 'SmartEdit_export.pot',
              'SmartEdit_transitions.pot', 'SmartEdit_QtUi.pot', 'SmartEdit_QtUi.ts']
for temp_file_name in temp_files:
    temp_file_path = os.path.join(language_folder_path, temp_file_name)
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)


log.info("-----------------------------------------------------")
log.info(" The SmartEdit.pot file has been successfully created ")
log.info(" with all text in SmartEdit.")
log.info("")
log.info(" Checking for duplicate keys...")
log.info("-----------------------------------------------------")




all_strings = {}

for pot_file in [
    'SmartEdit.pot',
    'SmartEdit_transitions.pot',
    'SmartEdit_blender.pot',
    'SmartEdit_emojis.pot',
]:
    with open(os.path.join(language_folder_path, "SmartEdit", pot_file)) as f:
        data = f.read()
        for key in re.findall('^msgid \"(.*)\"', data, re.MULTILINE):
            if key not in all_strings:
                all_strings[key] = "%s | %s" % (key, pot_file)
            elif key and key not in ('translator-credits', ):
                log.info(' ERROR: Duplicate key found: %s::%s' % (pot_file, all_strings[key]))
