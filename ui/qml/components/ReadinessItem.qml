import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    id: root
    property string name: "Item"
    property string statusText: "Unknown"
    property string status: "unknown"
    property string detail: ""
    implicitHeight: 72
    radius: Theme.radius.medium
    color: Theme.colors.surfaceHover
    border.color: Theme.colors.border

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.md
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Text { text: root.name; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.medium }
            Text { text: root.detail; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; elide: Text.ElideMiddle; Layout.fillWidth: true }
        }
        StatusBadge { text: root.statusText; status: root.status }
    }
}
