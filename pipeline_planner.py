# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PipelinePlanner
                                 A QGIS plugin
 Allow the user to create a line and evaluate impacts
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-09-21
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Miller Mountain LLC
        email                : mmllc@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QTableWidgetItem

from qgis.core import QgsProject

from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .pipeline_planner_dialog import PipelinePlannerDialog
import os.path


class PipelinePlanner:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        self.addPipelinePoint = QgsMapToolEmitPoint(self.canvas)
        self.rbPipeline = QgsRubberBand(self.canvas)
        self.rbPipeline.setColor(Qt.red)
        self.rbPipeline.setWidth(4)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'PipelinePlanner_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Pipeline Planner')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.dlg = PipelinePlannerDialog()
        self.dlg.tblImpacts.setColumnWidth(1, 7)
        self.dlg.tblImpacts.setColumnWidth(2, 250)
        self.dlg.tblImpacts.setColumnWidth(3, 75)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('PipelinePlanner', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/pipeline_planner/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Pipeline Planner'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
        self.addPipelinePoint.canvasClicked.connect(self.evaluatePipeline)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Pipeline Planner'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""
        
        self.canvas.setMapTool(self.addPipelinePoint)

    def evaluatePipeline(self, point, button):
        if button == Qt.LeftButton:
           self.rbPipeline.addPoint(point)
           self.rbPipeline.show()
        elif button == Qt.RightButton:
            pipeline = self.rbPipeline.asGeometry()
            self.dlg.tblImpacts.setRowCount(0)
            lyrRaptor = QgsProject.instance().mapLayersByName("Raptor Buffer")[0]

            raptors = lyrRaptor.getFeatures(pipeline.boundingBox())
            
            for raptor in raptors:
                valConstraint = raptor.attribute("recentspec")
                valID = raptor.attribute("Nest_ID")
                valStatus = raptor.attribute("recentstat")
                valDistance = pipeline.distance(raptor.geometry().centroid())
                if raptor.geometry().intersects(pipeline):
                   row = self.dlg.tblImpacts.rowCount()
                   self.dlg.tblImpacts.insertRow(row)
                   self.dlg.tblImpacts.setItem(row, 0, QTableWidgetItem(valConstraint))
                   self.dlg.tblImpacts.setItem(row, 1, QTableWidgetItem(str(valID)))
                   self.dlg.tblImpacts.setItem(row, 2, QTableWidgetItem(valStatus))
                   self.dlg.tblImpacts.setItem(row, 3, QTableWidgetItem("{:4.5f}".format(valDistance)))
                   
            lyrEagle = QgsProject.instance().mapLayersByName("BAEA Buffer")[0]

            eagles = lyrEagle.getFeatures(pipeline.boundingBox())
            
            for eagle in eagles:
                valConstraint = "BAEA Nest"
                valID = eagle.attribute("nest_id")
                valStatus = eagle.attribute("status")
                valDistance = pipeline.distance(eagle.geometry().centroid())
                if eagle.geometry().intersects(pipeline):
                   row = self.dlg.tblImpacts.rowCount()
                   self.dlg.tblImpacts.insertRow(row)
                   self.dlg.tblImpacts.setItem(row, 0, QTableWidgetItem(valConstraint))
                   self.dlg.tblImpacts.setItem(row, 1, QTableWidgetItem(str(valID)))
                   self.dlg.tblImpacts.setItem(row, 2, QTableWidgetItem(valStatus))
                   self.dlg.tblImpacts.setItem(row, 3, QTableWidgetItem("{:4.5f}".format(valDistance)))
                   
                   
            lyrBuowl = QgsProject.instance().mapLayersByName("BUOWL Buffer")[0]

            buowls = lyrBuowl.getFeatures(pipeline.boundingBox())
            
            for buowl in buowls:
                valConstraint = "BUOWL  Habitat"
                valID = buowl.attribute("habitat_id")
                valStatus = buowl.attribute("recentstat")
                valDistance = pipeline.distance(buowl.geometry().buffer(-0.001, 5))#usa un buffer porque el area no es un circulo sno un poligono
                if buowl.geometry().intersects(pipeline):
                   row = self.dlg.tblImpacts.rowCount()
                   self.dlg.tblImpacts.insertRow(row)
                   self.dlg.tblImpacts.setItem(row, 0, QTableWidgetItem(valConstraint))
                   self.dlg.tblImpacts.setItem(row, 1, QTableWidgetItem(str(valID)))
                   self.dlg.tblImpacts.setItem(row, 2, QTableWidgetItem(valStatus))
                   self.dlg.tblImpacts.setItem(row, 3, QTableWidgetItem("{:4.5f}".format(valDistance)))
               
            self.dlg.show()
               

            self.rbPipeline.reset()
