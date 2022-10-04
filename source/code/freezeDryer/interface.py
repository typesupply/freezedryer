import os
import AppKit
import ezui
from mojo.UI import HelpWindow, HTMLView
from mojo import extensions
from freezeDryer import core

# --------
# Projects
# --------

projectsDefaultsKey = "com.typesupply.FreezeDryer.projects"

class FDProjectsWindowController(ezui.WindowController):

    root = None
    settings = None

    def build(self):
        content = """
        = HorizontalStack

        |-------------|     @projectsTable
        |             |
        |-------------|
        > (+-)              @projectsTableAddRemoveButton
        > ({arrow.right})   @projectsGoToFolderButton

        * Tabs @projectTabs

          > Tab: Changes
           >> * HorizontalStack     @changesFilesStack
            >>> * VerticalStack
             >>>> Changed Files:
             >>>> |--|              @changesChangedFilesTable
            >>> * VerticalStack
             >>>> Ignored Files:
             >>>> |--|              @changesIgnoredFilesTable
           >> Message:
           >> [[__]]                @changesMessageEditor
           >> * HorizontalStack
            >>> (Commit)            @changesCommitButton
            >>> (Refresh)           @changesRefreshButton

          > Tab: History = HorizontalStack
           >> |--|                  @historyCommitTable
           >> * VerticalStack       @historyStateStack
            >>> |--|                @historyLogTable
            >>> * WebView           @historyReportView

          > Tab: Settings
           >> * TwoColumnForm                 @settingsForm
            >>> : Location:
            >>> /archive                      @settingsLocationLabel
            >>> (...)                         @settingsLocationActionButton
            >>> : Compression:
            >>> [ ] Convert to UFOZ           @settingsConvertToUFOZCheckbox
            >>> ( ) Use Aliases               @settingsAliasRadioGroup
            >>> ( ) Use Aliases Above 1 MB
            >>> (X) Never Use Aliases
            >>> : Glyph Set Proof:
            >>> [ ] Create                    @settingsGlyphSetProofCheckbox
            >>> : Visual Differences Report:
            >>> [ ] Create                    @settingsVisualDiffReportCheckbox
            >>> [ ] Lenient Comparisons       @settingsVisualDiffReportLenientCheckbox
            >>> [ ] Only Default Layer        @settingsVisualDiffReportDefaultLayerCheckbox
            >>> : Ignore:
            >>> [[__]]                        @settingsIgnorePatternsEditor
        """
        descriptionData = dict(
            content=dict(
                distribution="fill"
            ),

            projectsTable=dict(
                width=200,
                columnDescriptions=[
                    dict(
                        identifier="name"
                    )
                ],
                allowsMultipleSelection=False
            ),

            projectTabs=dict(
                width="fill"
            ),

            changesFilesStack=dict(
                distribution="fillEqually",
                height="fill"
            ),
            changesMessageEditor=dict(
                height=100
            ),
            changesRefreshButton=dict(
                gravity="trailing"
            ),

            historyCommitTable=dict(
                width=150
            ),
            historyStateStack=dict(
            ),
            historyLogTable=dict(
                height=200
            ),
            historyReportView=dict(
            ),

            settingsForm=dict(
                titleColumnWidth=200,
                itemColumnWidth=400,
                height="fill",
                width=0
            ),
            settingsLocationLabel=dict(
                width="fill"
            ),
            settingsLocationActionButton=dict(
                itemDescriptions=[
                    dict(
                        identifier="selectNewArchiveLocation",
                        text="Select Location…"
                    ),
                    dict(
                        identifier="useDefaultArchiveLocation",
                        text="Use Default Location"
                    )
                ]
            ),
            settingsIgnorePatternsEditor=dict(
                height=300,
            )
        )
        self.w = ezui.EZWindow(
            title="Freeze Dryer",
            content=content,
            descriptionData=descriptionData,
            controller=self,
            size=(1000, 800),
            minSize=(500, 500)
        )
        field = self.w.getItem("settingsLocationLabel").getNSTextField()
        field.setLineBreakMode_(AppKit.NSLineBreakByTruncatingHead)

        # frequently referenced items
        self.projectsTable = self.w.getItem("projectsTable")

    # Load and Launch

    def started(self):
        self._loadProjects()
        showWelcome = False
        if len(self.projectsTable.get()):
            self.projectsTable.setSelectedIndexes([0])
            self.projectsTableSelectionCallback(self.projectsTable)
        else:
            showWelcome = True
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
        self.projectsTable.set(items)

    def _writeProjects(self):
        projects = []
        for item in self.projectsTable.get():
            projects.append(item["path"])
        extensions.setExtensionDefault(projectsDefaultsKey, projects)

    def projectsTableSelectionCallback(self, sender):
        selection = sender.getSelectedIndexes()
        if not selection:
            self.disableProjectInterface()
        else:
            self.enableProjectInterface()
            item = sender.get()[selection[0]]
            path = item["path"]
            self.loadProject(path)

    def projectsTableAddRemoveButtonAddCallback(self, sender):
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
        items = list(self.projectsTable.get())
        if item not in items:
            items.append(item)
            self.projectsTable.set(items)
            self._writeProjects()
            self._loadProjects()

    def projectsTableAddRemoveButtonRemoveCallback(self, sender):
        items = list(self.projectsTable.get())
        for i in reversed(self.projectsTable.getSelectedIndexes()):
            del items[i]
        self.projectsTable.set(items)
        self._writeProjects()

    def projectsGoToFolderButtonCallback(self, sender):
        if self.root is None:
            return
        url = AppKit.NSURL.fileURLWithPath_(self.root)
        AppKit.NSWorkspace.sharedWorkspace().openURL_(url)

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
            self.loadCommitSettings()

    def disableProjectInterface(self):
        self.w.getItem("projectTabs").show(False)

    def enableProjectInterface(self):
        self.w.getItem("projectTabs").show(True)

    # Changes
    # -------

    def loadCommitSettings(self):
        self.updateIgnoredFilesTable()

    def changesCommitButtonCallback(self, sender):
        possible, message = core.canPerformCommit(self.root)
        if not possible:
            self.showMessage("The commit could not be completed.", message)
            return
        timeStamp = message
        messageEditor = self.w.getItem("changesMessageEditor")
        message = messageEditor.get()
        if not message:
            message = None
        progress = self.startProgress("Performing commit...")
        try:
            core.performCommit(self.root, timeStamp, message, progressBar=progress)
        finally:
            progress.close()
            messageEditor.set("")

    def updateIgnoredFilesTable(self):
        ignorePatterns = self.settings["ignore"]
        ignoredPaths = core.gatherIgnoredPaths(self.root, ignorePatterns)
        if not ignoredPaths:
            items = []
        else:
            items = [os.path.relpath(path, self.root) for path in ignoredPaths]
        self.w.getItem("changesIgnoredFilesTable").set(items)

    # Settings
    # --------

    _formToDefaults = dict(
        settingsLocationLabel="archiveDirectory",
        settingsConvertToUFOZCheckbox="compressUFOs",
        settingsGlyphSetProofCheckbox="makeGlyphSetProof",
        settingsVisualDiffReportCheckbox="makeVisualDiffsReport",
        settingsVisualDiffReportLenientCheckbox="normalizeDataInVisualDiffsReport",
        settingsVisualDiffReportDefaultLayerCheckbox="onlyDefaultLayerInVisualDiffsReport",
        # handled specially:
        # - alias
        # - ignore
    )

    def loadSettings(self):
        formContents = {
            itemIdentifier : self.settings[defaultsKey]
            for itemIdentifier, defaultsKey in self._formToDefaults.items()
        }
        formContents["settingsIgnorePatternsEditor"] = "\n".join(self.settings["ignore"])
        form = self.w.getItem("settingsForm")
        form.setItemValues(formContents)

    def storeSettings(self):
        core.writeSettings(self.root, self.settings)

    def settingsFormCallback(self, sender):
        values = self.w.getItem("settingsForm").getItemValues()
        for itemIdentifier, defaultsKey in self._formToDefaults.items():
            settings[defaultsKey] = values["itemIdentifier"]
        settings["ignore"] = [
            line for line
            in values["settingsIgnorePatternsEditor"].splitlines()
            if line.strip()
        ]
        self.storeSettings()

    def selectNewArchiveLocationCallback(self, sender):
        self.showGetFolder(
            callback=self._selectNewArchiveLocationResultCallback
        )

    def _selectNewArchiveLocationResultCallback(self, result):
        if result:
            self.settings["archiveDirectory"] = result[0]
            self.storeSettings()
            self.loadSettings()

    def useDefaultArchiveLocationCallback(self, sender):
        self.settings["archiveDirectory"] = core.getDefaultArchiveDirectory(self.root)
        self.storeSettings()
        self.loadSettings()

