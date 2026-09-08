ALL: ../src/classes/smartedit_rc.py
 
ICONS:=$(shell /usr/bin/find Humanity/ -type f -newer ../src/classes/smartedit_rc.py)
ICONS+=$(shell /usr/bin/find actions/ -type f -newer ../src/classes/smartedit_rc.py)
ICONS+=$(shell /usr/bin/find . -name \*-icon.svg -newer ../src/classes/smartedit_rc.py)
ICONS+=$(shell /usr/bin/find . -name cursor\*.png -newer ../src/classes/smartedit_rc.py)
ICONS+=$(shell /usr/bin/find . -name keyframe\*.png -newer ../src/classes/smartedit_rc.py)
ICONS+=AboutLogo.png AboutLogo@2x.png smartedit.svg
ICONS+=$(shell /usr/bin/find . -type f -name hw-accel\*.svg -newer ../src/classes/smartedit_rc.py)

../src/classes/smartedit_rc.py: smartedit.qrc $(ICONS)
	pyrcc5 smartedit.qrc -o $@
