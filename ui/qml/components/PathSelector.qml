import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Item {
    id: root
    property string title: "Folder"
    property string path: ""
    property bool showReset: true
    property bool showOpen: false
    signal browseRequested()
    signal resetRequested()
    signal openRequested()
    implicitHeight: 66
    Layout.fillWidth: true

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacing.lg
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            Text { text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.medium }
            Text { text: root.path; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; elide: Text.ElideMiddle; Layout.fillWidth: true }
        }
        SecondaryButton { visible: root.showOpen; text: "Open"; compact: true; onClicked: root.openRequested() }
        SecondaryButton { text: "Browse..."; compact: true; onClicked: root.browseRequested() }
        SecondaryButton { visible: root.showReset; text: "Reset"; compact: true; onClicked: root.resetRequested() }
    }
}
