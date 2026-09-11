import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import SPVideoStudio.Phase27 1.0
Rectangle {
    implicitWidth: label.implicitWidth + 24; implicitHeight: 28; radius: 9
    color: "transparent"; border.color: Theme.colors.border
    Text { id: label; anchors.centerIn: parent; text: Recovery.saveState; color: Recovery.saveState === "Save failed" ? Theme.colors.danger : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 11 }
}
