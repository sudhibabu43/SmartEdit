"""
 @file
 @brief This file loads the current language based on the computer's locale settings
 @author Noah Figg <eggmunkee@hotmail.com>
 @author Jonathan Thomas <jonathan@smartedit.org>

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
import locale

from qt_api import QLocale, QLibraryInfo, QTranslator, QCoreApplication

from classes.logger import log
from classes import info

try:
    from language import smartedit_lang  
    language_path = ":/locale/"
    log.debug("Using compiled translation resources")
except ImportError:
    language_path = os.path.join(info.PATH, 'language')
    log.debug("Loading translations from: {}".format(language_path))


def init_language():
    """ Find the current locale, and install the correct translators """

    
    app = QCoreApplication.instance()

    
    translator_types = (
        {"type": 'QT',
         "prefix": 'qt_',        
         "path": QLibraryInfo.location(QLibraryInfo.TranslationsPath)},
        {"type": 'QT',
         "prefix": 'qtbase_',    
         "path": QLibraryInfo.location(QLibraryInfo.TranslationsPath)},
        {"type": 'QT',
         "prefix": 'qt_',
         "path": os.path.join(info.PATH, 'language')}, 
        {"type": 'QT',
         "prefix": 'qtbase_',
         "path": os.path.join(info.PATH, 'language')}, 
        {"type": 'SmartEdit',
         "prefix": 'SmartEdit_',  
         "path": language_path},
    )

    
    locale_names = [os.environ.get('LANG', QLocale().system().name()),
                    os.environ.get('LOCALE', QLocale().system().name())
                    ]

    
    settings = app.get_settings()
    if settings:
        preference_lang = settings.get('default-language')
    else:
        preference_lang = "Default"

    
    log.info("Qt Detected Languages: {}".format(QLocale().system().uiLanguages()))
    log.info("LANG Environment Variable: {}".format(os.environ.get('LANG', "")))
    log.info("LOCALE Environment Variable: {}".format(os.environ.get('LOCALE', "")))
    log.info("SmartEdit Preference Language: {}".format(preference_lang))

    
    if preference_lang == "en_US":
        
        locale_names = [ "en_US" ]
    elif preference_lang != "Default":
        
        locale_names.insert(0, preference_lang)

    
    
    if info.CMDLINE_LANGUAGE:
        locale_names = [ info.CMDLINE_LANGUAGE ]
        log.info("Language overridden on command line, using: {}".format(info.CMDLINE_LANGUAGE))

    
    locale.setlocale(locale.LC_ALL, 'C')

    
    found_language = False
    for locale_name in locale_names:

        
        for type in translator_types:
            trans = QTranslator(app)
            if find_language_match(type["prefix"], type["path"], trans, locale_name):
                
                app.installTranslator(trans)
                found_language = True

        
        if found_language:
            log.debug("Exiting translation system (since we successfully loaded: {})".format(locale_name))
            info.CURRENT_LANGUAGE = locale_name
            break







def find_language_match(prefix, path, translator, locale_name):
    """ Match all combinations of locale, language, and country """

    filename = prefix + locale_name
    log.debug('Attempting to load {} in \'{}\''.format(filename,path))
    success = translator.load(filename, path)
    if success:
        log.debug('Successfully loaded {} in \'{}\''.format(filename, path))
    return success


def get_all_languages():
    """Get all language names and countries packaged with SmartEdit"""

    
    all_languages = []
    for locale_name in info.SUPPORTED_LANGUAGES:
        try:
            native_lang_name = QLocale(locale_name).nativeLanguageName().title()
            country_name = QLocale(locale_name).nativeCountryName().title()
            all_languages.append((locale_name, native_lang_name, country_name))
        except Exception:
            log.debug('Failed to parse language for %s', locale_name)

    
    return all_languages


def get_current_locale():
    return info.CURRENT_LANGUAGE
