import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Commands 1.0
Menu {
    property var controller
    property var clipData: ({})
    MenuItem { text:"Split at Playhead    "+Commands.shortcutFor("timeline.split"); enabled:clipData.sourceType === "scene_video" || clipData.sourceType === "scene_image"; onTriggered:if(controller)controller.splitSelected() }
    MenuItem { text:"Duplicate    "+Commands.shortcutFor("timeline.duplicate"); enabled:clipData.sourceType === "scene_video" || clipData.sourceType === "scene_image"; onTriggered:if(controller)controller.duplicateSelected() }
    MenuSeparator {}
    MenuItem { text:"Delete    "+Commands.shortcutFor("timeline.delete"); onTriggered:if(controller)controller.deleteSelected() }
}
