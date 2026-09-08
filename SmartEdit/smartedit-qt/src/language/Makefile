ALL: smartedit_lang.py

PYTHON ?= python3
PYRCC ?= pyrcc5

TRANSLATIONS:=$(shell /usr/bin/find ./ -type f -iname \*.qm -newer smartedit_lang.py)

smartedit_lang.py: smartedit_lang.qrc $(TRANSLATIONS)
	$(PYRCC) smartedit_lang.qrc -o $@
	$(PYTHON) neutralize_resource_import.py $@
