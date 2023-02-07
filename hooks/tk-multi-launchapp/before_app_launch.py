# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os, shutil, tempfile
import tank
from distutils.dir_util import copy_tree

class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """
    
    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute functon of the hook will be called prior to starting the required application        
        
        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.

        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > multi_launchapp = self.parent
        # > current_entity = multi_launchapp.context.entity

        # Add args to environment for debugging purposes
        os.environ["DEBUG_CONTEXT"] = str(self.parent.context)
        os.environ["DEBUG_ENGINE_NAME"] = str(engine_name)
        os.environ["DEBUG_APP_PATH"] = str(app_path)
        os.environ["DEBUG_APP_ARGS"] = str(app_args)
        os.environ["DEBUG_VERSION"] = str(version)
        
        #Get the top level dir for this version of the pipeline
        configDir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        os.environ["CONFIG_DIR"] = configDir
        os.environ["CONFIG_IS_DEV"] = "1" if configDir.startswith("C") else "0"
        configVersionDir = os.path.dirname(configDir)
        os.environ["CONFIG_VERSION_DIR"] = configVersionDir

        # Add BaitTasks vars
        os.environ["BAIT_TASKS_DIR"] = os.path.join(configVersionDir, "BaitTasks")
        os.environ["BAIT_TASKS_PYTHON_DIR"] = os.path.join(configVersionDir, "BaitTasks", "python")
        os.environ["BAIT_TASKS_NUKESCRIPTS_DIR"] = os.path.join(configVersionDir, "BaitTasks", "nukescripts")

        #Customise app inits
        if engine_name == "tk-nuke":
            #Remove the old pipeline customisations from the NUKE_PATH var.
            #Need to be careful to ensure that the SG path that is appended to the NUKE_PATH var remains.

            #Get current NUKE_PATH components
            nukePathComponents = os.environ["NUKE_PATH"].split(";")

            #Clear out the old pipeline path
            nukePathComponents = [x for x in nukePathComponents if x != "K:\\production03\\tools\\nuke"]

            #Add the new custom nuke init path
            baitNukeInitDir = os.path.join(configVersionDir, "BaitNukeInit", "core")
            nukePathComponents.append(baitNukeInitDir)

            #Add the submit to deadline tool
            baitSubmitToDeadlineDir = os.path.join(configVersionDir, "BaitSubmitNukeToDeadline")
            nukePathComponents.append(baitSubmitToDeadlineDir)

            #Join components and save
            os.environ["NUKE_PATH"] = ";".join(nukePathComponents)

        elif engine_name == "tk-hiero":
            #Get current HIERO_PLUGIN_PATH components
            hieroPluginPathComponents = os.environ["HIERO_PLUGIN_PATH"].split(";")

            # TODO: set path to current dir like the nuke.

            #Clear out the old pipeline path
            hieroPluginPathComponents = [x for x in hieroPluginPathComponents if x != "K:\\production03\\tools\\nuke"]

            #Add the new custom hiero init path
            hieroPluginInitDir = os.path.join(configVersionDir, "BaitNukeInit", "core")
            hieroPluginPathComponents.append(hieroPluginInitDir)

            #Join components and save
            os.environ["HIERO_PLUGIN_PATH"] = ";".join(hieroPluginPathComponents)

            #Add the startup task presets folder.
            # Hiero saves changes in a Hiero session to the imported presets.
            # In our case this means that a Hiero artist can override the pipeline config version of the template.
            # To prevent this, we copy the startup folder to a local temp location here.
            # This means that changes made to the template will not persist between sessions, and will
            # need to be made at a config level, as desired.

            # TODO: Move to custom Hiero Init repo?
            # Get the path to the startup folder
            hieroStartupFolderSource = os.path.join(configVersionDir, "tk-hiero-export", "startup")

            # Get the target path
            hieroStartupFolderTargetPath = os.path.join(tempfile.gettempdir(), "tk-hiero-export", "startup")
            
            # copy the new folder into place
            # copy_tree will overwrite existing files so no need to delete.
            try:
                if not os.path.exists(hieroStartupFolderTargetPath):
                    os.makedirs(hieroStartupFolderTargetPath)
                copy_tree(hieroStartupFolderSource, hieroStartupFolderTargetPath)
            except Exception as e:
                pass

            # Add the temp version to the Hiero plugin path
            hieroPluginPathComponents.append(hieroStartupFolderTargetPath)

            #Join components and save
            os.environ["HIERO_PLUGIN_PATH"] = ";".join(hieroPluginPathComponents)

        elif engine_name == "tk-blender":
            #We need to use a custom install of PySide 2 in order for the SG panels to load in Blender.
            #This is hosted on the network at
            networkPySide2InstallPath = "\\baitqn\Media\Core\Pipeline\python\Blender3.2\python"

            #However loading the above from the network causes Blender to freeze for 20-30s on startup each time.
            #To avoid this, we check for a local install of the above, copying it locally if needed, and then use that local version
            localPySide2InstallPath = os.path.join(os.environ["APPDATA"], "shotgrid_pipeline", "python", "Blender3.2", "python")
            
            #If the local copy doesn't exist
            if not os.path.exists(localPySide2InstallPath):
                print("tk-blender: Local PySide install doesn't exist.")
                if not os.path.exists(os.path.dirname(localPySide2InstallPath)):
                    print("tk-blender: Making containing dir")
                    os.makedirs(os.path.dirname(localPySide2InstallPath))
                print("tk-blender: Copying network PySide to {}".format(localPySide2InstallPath))
                try:
                    shutil.copytree(networkPySide2InstallPath, localPySide2InstallPath)
                    print("tk-blender: Copy completed")
                except Exception as e:
                    print("tk-blender: ERROR. Could not localise PySide.")
                    print(e)
                
            #Tell Blender to use the local PySide path
            os.environ["PYSIDE2_PYTHONPATH"] = localPySide2InstallPath