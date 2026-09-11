import QtQuick 2.15
import QtQuick.Controls 2.15
Menu {
    property var controller
    property var clipData: ({})
    MenuItem { text:"Split at Playhead"; enabled:clipData.sourceType === "scene_video" || clipData.sourceType === "scene_image"; onTriggered:if(controller)controller.splitSelected() }
    MenuItem { text:"Duplicate"; enabled:clipData.sourceType === "scene_video" || clipData.sourceType === "scene_image"; onTriggered:if(controller)controller.duplicateSelected() }
    MenuSeparator {}
    MenuItem { text:"Delete"; onTriggered:if(controller)controller.deleteSelected() }
}
