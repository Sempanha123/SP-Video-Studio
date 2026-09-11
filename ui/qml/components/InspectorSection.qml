import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
ColumnLayout {
    id: root
    property string title: ""
    property bool expanded: true
    property alias content: body.data
    spacing: expanded ? Theme.spacing.sm : 0
    Button {
        Layout.fillWidth: true; implicitHeight: 30
        contentItem: RowLayout { Text { text: root.expanded ? "⌄" : "›"; color: Theme.colors.textMuted; font.pixelSize: 15 }; Text { Layout.fillWidth: true; text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.small; font.weight: Theme.type.semibold } }
        background: Rectangle { color: parent.hovered ? Theme.colors.surfaceHover : "transparent"; radius: Theme.radius.small }
        onClicked: root.expanded = !root.expanded
    }
    ColumnLayout { id: body; visible: root.expanded; Layout.fillWidth: true; spacing: Theme.spacing.sm }
}
