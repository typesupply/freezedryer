import os
import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.UI import HelpWindow, HTMLView
from mojo import extensions
from freezeDryer import core

# --------
# Projects
# --------

projectsDefaultsKey = "com.typesupply.FreezeDryer.projects"

class FDProjectsWindowController(BaseWindowController):

    def __init__(self):
        self.root = None
        self.settings = {}

        self.w = vanilla.Window(
            (800, 600),
            "Freeze Dryer"
        )

        # --------
        # Projects
        # --------

        self.w.projectsList = vanilla.List(
            "auto",
            [],
            columnDescriptions=[
                dict(
                    title="name"
                )
            ],
            selectionCallback=self.projectsListSelectionCallback,
            allowsMultipleSelection=False,
            showColumnTitles=False,
            drawFocusRing=False
        )
        self.w.projectsSegmentedButtons = vanilla.SegmentedButton(
            "auto",
            [
                dict(title="+"),
                dict(title="-")
            ],
            selectionStyle="momentary",
            sizeStyle="regular",
            callback=self.projectsSegmentedButtonsCallback
        )

        # -------
        # Project
        # -------

        self.w.tabsContainer = vanilla.Group("auto")
        self.w.tabsContainer.line = vanilla.HorizontalLine("auto")
        self.w.tabsContainer.flex1 = vanilla.Group("auto")
        self.w.tabsContainer.tabsButtons = vanilla.SegmentedButton(
            "auto",
            [
                dict(title="Commit"),
                dict(title="Differences"),
                dict(title="Settings")
            ],
            sizeStyle="regular",
            callback=self.tabsButtonsCallback
        )
        self.w.tabsContainer.flex2 = vanilla.Group("auto")
        self.commitTab = self.w.tabsContainer.commitTab = vanilla.Group("auto")
        self.diffsTab = self.w.tabsContainer.diffsTab = vanilla.Group("auto")
        self.settingsTab = self.w.tabsContainer.settingsTab = vanilla.Group("auto")

        # Commit

        self.commitTab.messageTextEditor = vanilla.TextEditor(
            "auto"
        )
        self.commitTab.ignoredTextEditor = vanilla.TextEditor(
            "auto",
            readOnly=True
        )
        self.commitTab.commitButton = vanilla.Button(
            "auto",
            "Commit State",
            callback=self.commitButtonCallback
        )

        # Diffs

        self.diffsTab.compileReportTitle = vanilla.TextBox(
            "auto",
            "Compile Report"
        )
        self.diffsTab.compileReportLine = vanilla.HorizontalLine("auto")
        self.diffsTab.state1Title = vanilla.TextBox(
            "auto",
            "Before:"
        )
        self.diffsTab.state1PopUpButton = vanilla.PopUpButton(
            "auto",
            []
        )
        self.diffsTab.state2Title = vanilla.TextBox(
            "auto",
            "After:"
        )
        self.diffsTab.state2PopUpButton = vanilla.PopUpButton(
            "auto",
            []
        )
        self.diffsTab.lenientCheckBox = vanilla.CheckBox(
            "auto",
            "Lenient Comparisons"
        )
        self.diffsTab.onlyDefaultLayerCheckBox = vanilla.CheckBox(
            "auto",
            "Only Default Layer"
        )
        self.diffsTab.compileReportButton = vanilla.Button(
            "auto",
            "Compile",
            callback=self.diffsProcessButtonCallback
        )

        # Settings

        self.settingsTab.archiveLocationTitle = vanilla.TextBox(
            "auto",
            "Archive Location:"
        )
        self.settingsTab.archiveLocationLine = vanilla.HorizontalLine("auto")
        self.settingsTab.archiveLocationTextBox = vanilla.TextBox(
            "auto",
            ""
        )
        self.settingsTab.archiveLocationChangeButton = vanilla.Button(
            "auto",
            "Change",
            callback=self.settingsChooseLocationButtonCallback
        )
        self.settingsTab.archiveLocationDefaultButton = vanilla.Button(
            "auto",
            "Use Standard",
            callback=self.settingsArchiveLocationDefaultButtonCallback
        )

        self.settingsTab.filesTitle = vanilla.TextBox(
            "auto",
            "Files:"
        )
        self.settingsTab.filesLine = vanilla.HorizontalLine("auto")
        self.settingsTab.compressUFOsCheckBox = vanilla.CheckBox(
            "auto",
            "Convert UFO to UFOZ",
            callback=self.settingsCompressUFOsCheckBoxCallback
        )
        self.settingsTab.makeGlyphSetProofCheckBox = vanilla.CheckBox(
            "auto",
            "Make Glyph Set Proof",
            callback=self.settingsMakeGlyphSetProofCheckBoxCallback
        )
        self.settingsTab.makeVisualDiffsReportCheckBox = vanilla.CheckBox(
            "auto",
            "Make Visual Differences Report",
            callback=self.settingsMakeVisualDiffsReportCheckBoxCallback
        )
        self.settingsTab.lenientVisualDiffsReportCheckBox = vanilla.CheckBox(
            "auto",
            "Lenient Comparisons",
            callback=self.settingsLenientVisualDiffsReportCheckBoxCallback
        )
        self.settingsTab.onlyDefaultLayerVisualDiffsReportCheckBox = vanilla.CheckBox(
            "auto",
            "Only Default Layer",
            callback=self.settingsOnlyDefaultLayerVisualDiffsReportCheckBoxCallback
        )
        self.settingsTab.ignoreTitle = vanilla.TextBox(
            "auto",
            "Ignore:"
        )
        self.settingsTab.ignoreTextEditor = vanilla.TextEditor(
            "auto",
            "",
            callback=self.settingsIgnoreTextEditorCallback
        )

        # ----------------
        # Auto Positioning
        # ----------------

        metrics = dict(
            margin=15,
            padding=10,
            vButtonCenter=25,
            sectionPadding=30,
            indent=20
        )

        # Base

        rules = [
            "H:|-margin-[projectsList(==250)]-margin-[tabsContainer]-margin-|",
            "H:|-margin-[projectsSegmentedButtons]",
            "V:|-margin-[projectsList]-padding-[projectsSegmentedButtons]-margin-|",
            "V:|-margin-[tabsContainer]-margin-|",
        ]
        self.w.addAutoPosSizeRules(rules, metrics)

        # Project

        rules = [
            "H:|[line]|",
            "H:|-[flex1]-[tabsButtons]-[flex2(==flex1)]-|",
            "H:|[commitTab]|",
            "H:|[diffsTab]|",
            "H:|[settingsTab]|",
            "V:|"
                "-vButtonCenter-"
                "[line]",
            "V:|"
                "-margin-"
                "[tabsButtons]",
            "V:"
                "[tabsButtons]"
                "-margin-"
                "[commitTab]"
                "|",
            "V:"
                "[tabsButtons]"
                "-margin-"
                "[diffsTab]"
                "|",
            "V:"
                "[tabsButtons]"
                "-margin-"
                "[settingsTab]"
                "|",

        ]
        self.w.tabsContainer.addAutoPosSizeRules(rules, metrics)

        # Commit

        rules = [
            "H:|[messageTextEditor]|",
            "H:|[ignoredTextEditor]|",
            "H:[commitButton]|",
            "V:|"
                "[messageTextEditor]"
                "-padding-"
                "[ignoredTextEditor(==150)]"
                "-padding-"
                "[commitButton]"
                "|",
        ]
        self.commitTab.addAutoPosSizeRules(rules, metrics)

        # Diffs

        rules = [
            "H:|[compileReportTitle]",
            "H:|[compileReportLine]|",
            "H:|[state1Title]",
            "H:|[state1PopUpButton(==300)]",
            "H:|[state2Title]",
            "H:|[state2PopUpButton(==300)]",
            "H:[lenientCheckBox]",
            "H:[onlyDefaultLayerCheckBox]",
            "H:[compileReportButton]",
            "V:|"
                "[compileReportTitle]"
                "-padding-"
                "[compileReportLine]"
                "-padding-"
                "[state1Title]"
                "-padding-"
                "[state1PopUpButton]"
                "-padding-"
                "[state2Title]"
                "-padding-"
                "[state2PopUpButton]"
                "-padding-"
                "[lenientCheckBox]"
                "[onlyDefaultLayerCheckBox]"
                "-margin-"
                "[compileReportButton]",
        ]
        self.diffsTab.addAutoPosSizeRules(rules, metrics)

        # Settings

        rules = [
            "H:|[archiveLocationTitle]|",
            "H:|[archiveLocationLine]|",
            "H:|[archiveLocationTextBox]|",
            "H:|[archiveLocationChangeButton(==archiveLocationDefaultButton)]-padding-[archiveLocationDefaultButton(==archiveLocationChangeButton)]",
            "H:|[filesTitle]|",
            "H:|[filesLine]|",
            "H:|[compressUFOsCheckBox]",
            "H:|[makeGlyphSetProofCheckBox]",
            "H:|[makeVisualDiffsReportCheckBox]",
            "H:|-indent-[lenientVisualDiffsReportCheckBox]",
            "H:|-indent-[onlyDefaultLayerVisualDiffsReportCheckBox]",
            "H:|[ignoreTitle]|",
            "H:|[ignoreTextEditor]|",

            "V:|"
                "[archiveLocationTitle]"
                "-padding-"
                "[archiveLocationLine]"
                "-padding-"
                "[archiveLocationTextBox]",
            "V:"
                "[archiveLocationTextBox]"
                "-padding-"
                "[archiveLocationChangeButton]",
            "V:"
                "[archiveLocationTextBox]"
                "-padding-"
                "[archiveLocationDefaultButton]",

            "V:"
                "[archiveLocationDefaultButton]"
                "-sectionPadding-"
                "[filesTitle]"
                "-padding-"
                "[filesLine]"
                "-padding-"
                "[compressUFOsCheckBox]"
                "[makeGlyphSetProofCheckBox]"
                "[makeVisualDiffsReportCheckBox]"
                "[lenientVisualDiffsReportCheckBox]"
                "[onlyDefaultLayerVisualDiffsReportCheckBox]"
                "-padding-"
                "[ignoreTitle]"
                "-padding-"
                "[ignoreTextEditor(==100)]"
        ]
        self.settingsTab.addAutoPosSizeRules(rules, metrics)

        # Load and Launch

        self._loadProjects()
        showWelcome = False
        if len(self.w.projectsList):
            self.w.projectsList.setSelection([0])
        else:
            showWelcome = True
        self.w.tabsContainer.tabsButtons.set(0)
        self.tabsButtonsCallback(self.w.tabsContainer.tabsButtons)
        self.w.open()
        if showWelcome:
            self.showWelcomeMessage()

    def showWelcomeMessage(self):
        htmlPath = os.path.dirname(__file__)
        htmlPath = os.path.dirname(htmlPath)
        htmlPath = os.path.dirname(htmlPath)
        htmlPath = os.path.join(htmlPath, "html", "index.html")
        w = HelpWindow(developer="Type Supply", developerURL="http://typesupply.com")
        w.setHTMLPath(htmlPath)

    # --------
    # Projects
    # --------

    def _wrapPath(self, path):
        name = os.path.basename(path)
        item = dict(name=name, path=path)
        return item

    def _loadProjects(self):
        projects = extensions.getExtensionDefault(projectsDefaultsKey, [])
        items = []
        for path in projects:
            item = self._wrapPath(path)
            items.append((item["name"], item))
        items.sort()
        items = [item[-1] for item in items]
        self.w.projectsList.set(items)

    def _writeProjects(self):
        projects = []
        for item in self.w.projectsList.get():
            projects.append(item["path"])
        extensions.setExtensionDefault(projectsDefaultsKey, projects)

    def projectsListSelectionCallback(self, sender):
        selection = sender.getSelection()
        if not selection:
            self.disableProjectInterface()
        else:
            self.enableProjectInterface()
            item = sender[selection[0]]
            path = item["path"]
            self.loadProject(path)

    def projectsSegmentedButtonsCallback(self, sender):
        value = sender.get()
        if value == 0:
            self.addProjectButtonCallback()
        elif value == 1:
            self.removeProjectButtonCallback()

    def addProjectButtonCallback(self):
        self.showGetFolder(callback=self._addProjectButtonCallback)

    def _addProjectButtonCallback(self, result):
        if not result:
            return
        directory = result[0]
        # needs to be initialized
        if not core.haveSettings(directory):
            isViable, message = core.isViableRoot(directory)
            # uh oh
            if not isViable:
                self.showMessage(
                    "Unable to add project.",
                    message
                )
                return
            # initialize
            else:
                settings = core.getDefaultSettings(directory)
                core.initializeProject(directory, settings)
        # do it
        item = self._wrapPath(directory)
        if item not in self.w.projectsList.get():
            self.w.projectsList.append(item)
            self._writeProjects()
            self._loadProjects()

    def removeProjectButtonCallback(self):
        for i in reversed(self.w.projectsList.getSelection()):
            del self.w.projectsList[i]
        self._writeProjects()

    # -------
    # Project
    # -------

    def loadProject(self, path):
        if not core.haveSettings(path):
            self.showMessage(
                "The settings file is missing.",
                "Don't delete the settings file."
            )
            self.disableProjectInterface()
        else:
            self.root = path
            self.settings = core.readSettings(self.root)
            self.loadSettings()
            self.loadDiffSettings()
            self.loadCommitSettings()

    def disableProjectInterface(self):
        self.w.tabsContainer.show(False)

    def enableProjectInterface(self):
        self.w.tabsContainer.show(True)

    def tabsButtonsCallback(self, sender):
        index = sender.get()
        self.commitTab.show(index == 0)
        self.diffsTab.show(index == 1)
        self.settingsTab.show(index == 2)

    # Commit
    # ------

    def loadCommitSettings(self):
        self.updateIgnoredTextEditor()

    def commitButtonCallback(self, sender):
        possible, message = core.canPerformCommit(self.root)
        if not possible:
            self.showMessage("The commit could not be completed.", message)
            return
        timeStamp = message
        message = self.commitTab.messageTextEditor.get()
        if not message:
            message = None
        progress = self.startProgress("Performing commit...")
        try:
            core.performCommit(self.root, timeStamp, message, progressBar=progress)
        finally:
            progress.close()
            self.commitTab.messageTextEditor.set("")

    def updateIgnoredTextEditor(self):
        ignorePatterns = self.settings["ignore"]
        ignoredPaths = core.gatherIgnoredPaths(self.root, ignorePatterns)
        if not ignoredPaths:
            text = "No files will be ignored."
        else:
            text = ["Ignored Files:"]
            text += [os.path.relpath(path, self.root) for path in ignoredPaths]
            text = "\n".join(text)
        self.commitTab.ignoredTextEditor.set(text)

    # Diffs
    # -----

    def loadDiffSettings(self):
        states = core.getDiffStateCandidates(self.root)
        self.diffsTab.state1PopUpButton.setItems(states)
        self.diffsTab.state2PopUpButton.setItems(states)

    def diffsProcessButtonCallback(self, sender):
        state1 = self.diffsTab.state1PopUpButton.get()
        state1 = self.diffsTab.state1PopUpButton.getItems()[state1]
        state2 = self.diffsTab.state2PopUpButton.get()
        state2 = self.diffsTab.state2PopUpButton.getItems()[state2]
        if state1 == state2:
            self.showMessage(
                "There are no differences.",
                "You picked the same state."
            )
            return
        report = core.compileDiffReport(
            self.root,
            state1,
            state2,
            normalize=self.diffsTab.lenientCheckBox.get(),
            onlyCompareFontDefaultLayers=self.diffsTab.onlyDefaultLayerCheckBox.get()
        )
        FDDiffWindowController(report)

    # Settings
    # --------

    def loadSettings(self):
        self.settingsTab.archiveLocationTextBox.set(
            self.settings["archiveDirectory"]
        )
        self.settingsTab.compressUFOsCheckBox.set(
            self.settings["compressUFOs"]
        )
        self.settingsTab.makeGlyphSetProofCheckBox.set(
            self.settings["makeGlyphSetProof"]
        )
        self.settingsTab.makeVisualDiffsReportCheckBox.set(
            self.settings["makeVisualDiffsReport"],
        )
        self.settingsTab.lenientVisualDiffsReportCheckBox.set(
            self.settings["normalizeDataInVisualDiffsReport"]
        )
        self.settingsTab.onlyDefaultLayerVisualDiffsReportCheckBox.set(
            self.settings["onlyDefaultLayerInVisualDiffsReport"]
        )
        self.settingsTab.ignoreTextEditor.set(
            "\n".join(self.settings["ignore"])
        )

    def _storeSettings(self):
        core.writeSettings(self.root, self.settings)

    def _updateSettingsArchiveLocation(self):
        self.settingsTab.archiveLocationTextBox.set(
            self.settings["archiveDirectory"]
        )

    def settingsChooseLocationButtonCallback(self, sender):
        self.showGetFolder(
            callback=self._settingsChooseLocationButtonCallback
        )

    def _settingsChooseLocationButtonCallback(self, result):
        if result:
            self.settings["archiveDirectory"] = result[0]
            self._storeSettings()
            self._updateSettingsArchiveLocation()

    def settingsArchiveLocationDefaultButtonCallback(self, sender):
        self.settings["archiveDirectory"] = core.getDefaultArchiveDirectory(self.root)
        self._storeSettings()
        self._updateSettingsArchiveLocation()

    def settingsCompressUFOsCheckBoxCallback(self, sender):
        self.settings["compressUFOs"] = sender.get()
        self._storeSettings()

    def settingsMakeGlyphSetProofCheckBoxCallback(self, sender):
        self.settings["makeGlyphSetProof"] = sender.get()
        self._storeSettings()

    def settingsMakeVisualDiffsReportCheckBoxCallback(self, sender):
        self.settings["makeVisualDiffsReport"] = sender.get()
        self._storeSettings()

    def settingsLenientVisualDiffsReportCheckBoxCallback(self, sender):
        self.settings["normalizeDataInVisualDiffsReport"] = sender.get()
        self._storeSettings()

    def settingsOnlyDefaultLayerVisualDiffsReportCheckBoxCallback(self, sender):
        self.settings["onlyDefaultLayerInVisualDiffsReport"] = sender.get()
        self._storeSettings()

    def settingsIgnoreTextEditorCallback(self, sender):
        patterns = [line.strip() for line in sender.get().splitlines() if line.strip()]
        self.settings["ignore"] = patterns
        self._storeSettings()
        self.updateIgnoredTextEditor()


# -----
# Diffs
# -----

class FDDiffWindowController(BaseWindowController):

    def __init__(self, html):
        self.w = vanilla.Window((800, 500), minSize=(200, 200))
        self.w.htmlView = HTMLView((0, 0, 0, 0))
        self.w.htmlView.setHTML(html)
        self.w.open()
