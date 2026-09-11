import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"
RowLayout {
    id:root; property var controller; property real viewportWidth: 900
    spacing:Theme.spacing.xs
    SecondaryButton { text:"◀"; compact:true; onClicked:if(controller)controller.previousScene() }
    AppButton { text:"Play / Pause"; compact:true; onClicked:if(controller)controller.togglePlayback() }
    SecondaryButton { text:"▶"; compact:true; onClicked:if(controller)controller.nextScene() }
    SecondaryButton { text:"Frame −"; compact:true; onClicked:if(controller)controller.stepFrame(-1) }
    SecondaryButton { text:"Frame +"; compact:true; onClicked:if(controller)controller.stepFrame(1) }
    SecondaryButton { text:"Split"; compact:true; enabled:controller && controller.selectedClip.id; onClicked:controller.splitSelected() }
    SecondaryButton { text:"Duplicate"; compact:true; enabled:controller && controller.selectedClip.id; onClicked:controller.duplicateSelected() }
    SecondaryButton { text:"Delete"; compact:true; enabled:controller && controller.selectedClip.id; onClicked:controller.deleteSelected() }
    Rectangle { width:1; height:24; color:Theme.colors.border }
    SecondaryButton { text:"Undo"; compact:true; enabled:controller && controller.canUndo; onClicked:controller.undo() }
    SecondaryButton { text:"Redo"; compact:true; enabled:controller && controller.canRedo; onClicked:controller.redo() }
    SecondaryButton { text:"Marker"; compact:true; onClicked:if(controller)controller.addMarker("Marker") }
    Item { Layout.fillWidth:true }
    AppSwitch { checked:controller ? controller.snapEnabled : true; text:"Snap"; onToggled:if(controller)controller.setSnapEnabled(checked) }
    SecondaryButton { text:"Fit"; compact:true; onClicked:if(controller)controller.fitTimeline(root.viewportWidth) }
    TimelineZoomControl { controller:root.controller }
}
