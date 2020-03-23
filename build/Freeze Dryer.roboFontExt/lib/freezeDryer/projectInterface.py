import os
import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from freezeDryer import core

class ProjectWindowController(BaseWindowController):

    def __init__(self, root, mode="commit"):
        if not core.haveSettings(root):
            vanilla.dialogs.message(
                "Unable to use the selected directory.",
                "The settings file is missing."
            )
            return

        self.root = root
        self.settings = core.readSettings(self.root)

        self.w = vanilla.Window(
            (500, 500),
            "Freeze Dryer: %s" % os.path.basename(self.root)
        )

        # ----
        # Tabs
        # ----

        self.w.flex1 = vanilla.Group("auto")
        self.w.flex2 = vanilla.Group("auto")
        self.w.tabsButtons = vanilla.SegmentedButton(
            "auto",
            [
                dict(title="Commit"),
                dict(title="Settings")
            ],
            sizeStyle="regular",
            callback=self.tabsButtonsCallback
        )
        self.w.tabsLine = vanilla.HorizontalLine("auto")
        self.w.commitTab = vanilla.Group("auto")
        self.w.settingsTab = vanilla.Group("auto")

        if mode == "commit":
            index = 0
        elif mode == "settings":
            index = 1
        self.w.tabsButtons.set(index)
        self.tabsButtonsCallback(self.w.tabsButtons)

        metrics = dict(
            margin=15,
            padding=10,
            sectionPadding=30
        )
        rules = [
            "H:|-[flex1]-[tabsButtons]-[flex2(==flex1)]-|",
            "H:|-margin-[tabsLine]-margin-|",
            "H:|[commitTab]|",
            "H:|[settingsTab]|",
            "V:|"
                "-margin-"
                "[tabsButtons]"
                "-margin-"
                "[tabsLine]",
            "V:"
                "[tabsLine]"
                "[commitTab]"
                "|",
            "V:"
                "[tabsLine]"
                "[settingsTab]"
                "|",

        ]
        self.w.addAutoPosSizeRules(rules, metrics)

        # ------
        # Commit
        # ------

        self.w.commitTab.messageTextEditor = vanilla.TextEditor(
            "auto"
        )
        self.w.commitTab.commitButton = vanilla.Button(
            "auto",
            "Commit State",
            callback=self.commitButtonCallback
        )

        rules = [
            "H:|-margin-[messageTextEditor]-margin-|",
            "H:[commitButton]-margin-|",
            "V:|"
                "-margin-"
                "[messageTextEditor]"
                "-padding-"
                "[commitButton]"
                "-margin-"
                "|",
        ]
        self.w.commitTab.addAutoPosSizeRules(rules, metrics)

        # --------
        # Settings
        # --------

        self.w.settingsTab.archiveLocationTitle = vanilla.TextBox(
            "auto",
            "Archive Location:"
        )
        self.w.settingsTab.archiveLocationLine = vanilla.HorizontalLine("auto")
        self.w.settingsTab.archiveLocationTextBox = vanilla.TextBox(
            "auto",
            self.settings["archiveDirectory"]
        )
        self.w.settingsTab.archiveLocationChangeButton = vanilla.Button(
            "auto",
            "Change",
            callback=self.settingsChooseLocationButtonCallback
        )
        self.w.settingsTab.archiveLocationDefaultButton = vanilla.Button(
            "auto",
            "Standard",
            callback=self.settingsArchiveLocationDefaultButtonCallback
        )

        self.w.settingsTab.filesTitle = vanilla.TextBox(
            "auto",
            "Files:"
        )
        self.w.settingsTab.filesLine = vanilla.HorizontalLine("auto")
        self.w.settingsTab.compressUFOsCheckBox = vanilla.CheckBox(
            "auto",
            "Convert UFO to UFOZ",
            value=self.settings["compressUFOs"],
            callback=self.settingsCompressUFOsCheckBoxCallback
        )

        rules = [
            "H:|-margin-[archiveLocationTitle]-margin-|",
            "H:|-margin-[archiveLocationLine]-margin-|",
            "H:|-margin-[archiveLocationTextBox]-margin-|",
            "H:|-margin-[archiveLocationChangeButton(==archiveLocationDefaultButton)]-padding-[archiveLocationDefaultButton(==archiveLocationChangeButton)]",
            "H:|-margin-[filesTitle]-margin-|",
            "H:|-margin-[filesLine]-margin-|",
            "H:|-margin-[compressUFOsCheckBox]",

            "V:|"
                "-margin-"
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
        ]
        self.w.settingsTab.addAutoPosSizeRules(rules, metrics)

        # --
        # Go
        # --

        self.w.center()
        self.w.open()

    def tabsButtonsCallback(self, sender):
        index = sender.get()
        self.w.commitTab.show(index == 0)
        self.w.settingsTab.show(index == 1)

    # ------
    # Commit
    # ------

    def commitButtonCallback(self, sender):
        possible, message = core.canPerformCommit(self.root)
        if not possible:
            self.showMessage("The commit could not be completed.", message)
            return
        timeStamp = message
        message = self.w.commitTab.messageTextEditor.get()
        if not message:
            message = None
        progress = self.startProgress("Preforming commit...")
        try:
            core.performCommit(self.root, timeStamp, message)
        finally:
            progress.close()
            self.w.commitTab.messageTextEditor.set("")

    # --------
    # Settings
    # --------

    def _storeSettings(self):
        core.writeSettings(self.root, self.settings)

    def _updateSettingsArchiveLocation(self):
        self.w.settingsTab.archiveLocationTextBox.set(
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
