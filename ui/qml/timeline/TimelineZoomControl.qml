import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"
RowLayout {
    property var controller
    spacing: Theme.spacing.xs
    SecondaryButton { text:"−"; compact:true; onClicked: if (controller) controller.zoomOut() }
    Text { text: controller ? Math.round(controller.pixelsPerSecond)+" px/s" : ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    SecondaryButton { text:"+"; compact:true; onClicked: if (controller) controller.zoomIn() }
}
