import vanilla
from freezeDryer import core
from freezeDryer.projectInterface import ProjectWindowController

def run():
    results = vanilla.dialogs.getFolder()
    if not results:
        return
    directory = results[0]
    isViable, message = core.isViableRoot(directory)
    if not isViable:
        vanilla.dialogs.message(
            "Unable to initialize project.",
            message
        )
        return
    settings = core.getDefaultSettings(directory)
    core.initializeProject(directory, settings)
    ProjectWindowController(directory, mode="settings")

if __name__ == "__main__":
    run()