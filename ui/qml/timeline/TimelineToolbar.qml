import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../components"
import "../theme"
RowLayout {
    id:root; property var controller; property real viewportWidth: 900
    spacing:Theme.spacing.xs
    SecondaryButton { text:"◀"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Previous scene";onClicked:if(controller)controller.previousScene() }
    AppButton { text:"Play / Pause"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Play / Pause · "+Commands.shortcutFor("playback.toggle");onClicked:if(controller)controller.togglePlayback() }
    SecondaryButton { text:"▶"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Next scene";onClicked:if(controller)controller.nextScene() }
    SecondaryButton { text:"Frame −"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Previous frame · "+Commands.shortcutFor("playback.frame_previous");onClicked:if(controller)controller.stepFrame(-1) }
    SecondaryButton { text:"Frame +"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Next frame · "+Commands.shortcutFor("playback.frame_next");onClicked:if(controller)controller.stepFrame(1) }
    SecondaryButton { text:"Split"; compact:true; enabled:controller && controller.selectedClip.id; ToolTip.visible:hovered;ToolTip.text:"Split · "+Commands.shortcutFor("timeline.split");onClicked:controller.splitSelected() }
    SecondaryButton { text:"Duplicate"; compact:true; enabled:controller && controller.selectedClip.id; ToolTip.visible:hovered;ToolTip.text:"Duplicate · "+Commands.shortcutFor("timeline.duplicate");onClicked:controller.duplicateSelected() }
    SecondaryButton { text:"Delete"; compact:true; enabled:controller && controller.selectedClip.id; ToolTip.visible:hovered;ToolTip.text:"Delete · "+Commands.shortcutFor("timeline.delete");onClicked:controller.deleteSelected() }
    Rectangle { width:1; height:24; color:Theme.colors.border }
    SecondaryButton { text:"Undo"; compact:true; enabled:controller && controller.canUndo; ToolTip.visible:hovered;ToolTip.text:(controller&&controller.undoLabel?"Undo "+controller.undoLabel:"Undo")+" · "+Commands.shortcutFor("edit.undo");onClicked:controller.undo() }
    SecondaryButton { text:"Redo"; compact:true; enabled:controller && controller.canRedo; ToolTip.visible:hovered;ToolTip.text:(controller&&controller.redoLabel?"Redo "+controller.redoLabel:"Redo")+" · "+Commands.shortcutFor("edit.redo");onClicked:controller.redo() }
    SecondaryButton { text:"Marker"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Add Marker · "+Commands.shortcutFor("timeline.marker");onClicked:if(controller)controller.addMarker("Marker") }
    Item { Layout.fillWidth:true }
    AppSwitch { checked:controller ? controller.snapEnabled : true; text:"Snap"; ToolTip.visible:hovered;ToolTip.text:"Toggle Snap · "+Commands.shortcutFor("timeline.snap");onToggled:if(controller)controller.setSnapEnabled(checked) }
    SecondaryButton { text:"Fit"; compact:true; ToolTip.visible:hovered;ToolTip.text:"Fit Timeline · "+Commands.shortcutFor("timeline.fit");onClicked:if(controller)controller.fitTimeline(root.viewportWidth) }
    TimelineZoomControl { controller:root.controller }
}
