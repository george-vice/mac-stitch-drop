#!/usr/bin/env python3
"""Rebuilds "Send to Brother.workflow" (the Finder Quick Action bundle).

The bundle is committed to the repo, so you only need this if you change the
shell snippet below. Run:  python3 quickaction/build_workflow.py
"""
import os
import plistlib
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))

# What the Quick Action runs. Finder passes the selected files as arguments.
SCRIPT = r'''# Send to Brother — Finder Quick Action
DIR="$HOME/Library/Application Support/StitchDrop/quickaction"
LOG="$HOME/Library/Logs/StitchDrop.log"
for P in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$P" ] && "$P" -c 'import sys' >/dev/null 2>&1; then
    exec "$P" "$DIR/brother_quicksend.py" "$@" >>"$LOG" 2>&1
  fi
done
osascript -e 'display dialog "Send to Brother needs Python 3. Open Terminal, type python3, press Return and click Install. Then try again." with title "Send to Brother" buttons {"OK"} with icon caution'
'''


def new_uuid():
    return str(uuid.uuid4()).upper()


def arg(name, default):
    return {"default value": default, "name": name, "required": "0", "type": "0", "uuid": "0"}


action = {
    "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
    "AMActionVersion": "2.0.3",
    "AMApplication": ["Automator"],
    "AMParameterProperties": {k: {} for k in
                              ["COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell", "source"]},
    "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
    "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
    "ActionName": "Run Shell Script",
    "ActionParameters": {"COMMAND_STRING": SCRIPT, "CheckedForUserDefaultShell": True,
                         "inputMethod": 1,  # 1 = pass input as arguments
                         "shell": "/bin/bash", "source": ""},
    "BundleIdentifier": "com.apple.RunShellScript",
    "CFBundleVersion": "2.0.3",
    "CanShowSelectedItemsWhenRun": False,
    "CanShowWhenRun": True,
    "Category": ["AMCategoryUtilities"],
    "Class Name": "RunShellScriptAction",
    "InputUUID": new_uuid(), "OutputUUID": new_uuid(), "UUID": new_uuid(),
    "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
    "UnlocalizedApplications": ["Automator"],
    "arguments": {"0": arg("inputMethod", 0), "1": arg("CheckedForUserDefaultShell", False),
                  "2": arg("source", ""), "3": arg("COMMAND_STRING", ""), "4": arg("shell", "")},
    "isViewVisible": 1,
    "location": "309.000000:305.000000",
    "nibPath": "/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib",
}

workflow = {
    "AMApplicationBuild": "523", "AMApplicationVersion": "2.10", "AMDocumentVersion": "2",
    "actions": [{"action": action, "isViewVisible": 1}],
    "connectors": {},
    "workflowMetaData": {
        "applicationBundleIDsByPath": {}, "applicationPaths": [],
        "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
        "outputTypeIdentifier": "com.apple.Automator.nothing",
        "presentationMode": 15, "processesInput": 0,
        "serviceApplicationBundleID": "com.apple.finder",
        "serviceApplicationPath": "/System/Library/CoreServices/Finder.app",
        "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
        "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
        "serviceProcessesInput": 0,
        "systemImageName": "NSActionTemplate",
        "useAutomaticInputType": 0,
        "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
    },
}

info = {"NSServices": [{
    "NSBackgroundColorName": "background",
    "NSIconName": "NSActionTemplate",
    "NSMenuItem": {"default": "Send to Brother"},
    "NSMessage": "runWorkflowAsService",
    "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
    "NSSendFileTypes": ["public.item"],
}]}

if __name__ == "__main__":
    contents = os.path.join(HERE, "Send to Brother.workflow", "Contents")
    os.makedirs(contents, exist_ok=True)
    with open(os.path.join(contents, "document.wflow"), "wb") as f:
        plistlib.dump(workflow, f)
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(info, f)
    print("Wrote", os.path.dirname(contents))
