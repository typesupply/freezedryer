import vanilla
from freezeDryer import core
from freezeDryer.projectInterface import ProjectWindowController

def run():
    results = vanilla.dialogs.getFolder()
    if not results:
        return
    root = results[0]
    ProjectWindowController(root, mode="commit")

if __name__ == "__main__":
    run()